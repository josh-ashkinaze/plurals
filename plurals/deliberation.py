from typing import List, Optional, Dict, Any
import random
import warnings
from plurals.agent import Agent
from plurals.helpers import load_yaml, format_previous_responses
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from plurals.helpers import SmartString
import re

DEFAULTS = load_yaml("instructions.yaml")


class Moderator(Agent):
    """
    A moderator agent that combines responses from other agents at the end of structure processing.

    Args:
        persona (str, optional): The persona of the moderator. Default is 'default'.
        system_instructions (str, optional): The system instructions for the moderator. Default is None. If you pass in
            'auto', an LLM will generate its own system instructions automatically based on the task.
        combination_instructions (str, optional): The instructions for combining responses. Default is 'default'.
        model (str, optional): The model to use for the moderator. Default is 'gpt-4o'.
        task (str, optional): The task description for the moderator. By default, moderators will inherit the task
            from the Structure so this can be left blank. It is only required if you wish to manually generate system
            instructions outside of the Structure.
        kwargs (Optional[Dict]): Additional keyword arguments. These are from LiteLLM's completion function.
            (see here: https://litellm.vercel.app/docs/completion/input)

    Attributes:
        persona (str): The persona of the moderator.
        combination_instructions (str): The instructions for combining responses.
        system_instructions (str): The full system instructions for the moderator.

    **Examples:**
        **Auto-Moderator**

        If the system_instructions of a moderator are set to 'auto',
        then the moderator will, given a task, come up with its own system instructions.

        .. code-block:: python

            task = ("Your goal is to come up with the most creative ideas possible for pants. We are maximizing creativity. Answer"
            " in 20 words.")
            a = Agent(model='gpt-4o')
            b = Agent(model='gpt-3.5-turbo')
            chain = Chain([a, b], moderator=Moderator(system_instructions='auto', model='gpt-4o'), task=task)
            print(chain.moderator.system_instructions)

        .. code-block:: text

            Group similar ideas together, prioritize uniqueness and novelty. Highlight standout concepts and remove
            duplicates. Ensure the final list captures diverse and imaginative designs.
    """

    def __init__(
            self,
            persona: Optional[str] = None,
            system_instructions: Optional[str] = None,
            combination_instructions: str = "default",
            model: str = "gpt-4o",
            task: Optional[str] = None,
            kwargs: Optional[Dict] = None):

        if kwargs is None:
            kwargs = {}

        # Case 1: if both persona and system_instructions are provided, raise a ValueError
        if persona and system_instructions and system_instructions != 'auto':
            raise ValueError("Cannot provide both persona and system instructions")

        # Case 2: if system_instructions is 'auto', generate system instructions using an LLM
        if system_instructions == 'auto':
            self.model = model
            self.kwargs = kwargs
            self.system_instructions = self.generate_system_instructions(task=task)

        # Case 3: if only persona is provided, use persona with dummy persona template ${persona}
        if persona and not system_instructions:
            persona_template = "${persona}"
            persona_value = DEFAULTS["moderator"]['persona'].get(persona, persona)
            super().__init__(persona=persona_value, persona_template=persona_template, model=model, kwargs=kwargs)

        # Case 4: if only system_instructions is provided, set system_instructions and set persona and persona_template to None
        elif system_instructions and not persona:
            super().__init__(system_instructions=system_instructions, persona=None, persona_template=None, model=model,
                             kwargs=kwargs)

        # Case 5: if neither persona nor system_instructions are provided, use default persona
        else:
            default_persona = DEFAULTS["moderator"]['persona'].get('default', 'default_moderator_persona')
            super().__init__(persona=default_persona, persona_template="${persona}", model=model, kwargs=kwargs)

        self.combination_instructions = DEFAULTS["moderator"]['combination_instructions'].get(combination_instructions,
                                                                                              combination_instructions)

    def generate_system_instructions(self, task: str, max_tries: int = 10) -> str:
        """
        Generate and instructions using an LLM and a task. This function will not automatically set the system
        instructions, but it will return the generated system instructions (so you can inspect or re-generate them).
        Then you can set system instructions using the `system_instructions` attribute.

        See `generate_and_set_system_instructions` for a function that will generate and set the system instructions.

        Args:
            task (str): The task description for which system instructions need to be generated.
            max_tries (int, optional): The maximum number of attempts to generate valid system instructions. Default is 10.

        Returns:
            str: The generated system instructions.

        Raises:
            ValueError: If valid system instructions are not generated after the maximum number of attempts.
        """

        for _ in range(max_tries):
            prompt = (f"INSTRUCTIONS\nA moderator LLM will see responses for the following task: {task}. Generate "
                      f"system instructions for the moderator to best aggregate these responses after all responses are "
                      f"submitted. Return system instructions and nothing else. Instructions should be 50 words or "
                      f"less and start with 'System Instructions':\n"
                      f"System Instructions:")
            try:
                response = Agent(task=prompt, model=self.model, kwargs=self.kwargs).process()
                # Check if the response starts with "System Instructions:" (case-insensitive and allows for spaces)
                # Remove the "System Instructions:" part and any leading/trailing whitespace
                if re.match(r"^\s*system\s+instructions\s*:\s*", response, re.IGNORECASE):
                    system_instructions = re.sub(r"^\s*system\s+instructions\s*:\s*", "", response,
                                                 flags=re.IGNORECASE).strip()
                    return system_instructions
            except Exception as e:
                print(f"Attempt failed with error: {e}")

        raise ValueError("Failed to generate valid system instructions after max tries.")

    def generate_and_set_system_instructions(self, task: str, max_tries: int = 10) -> None:
        """
        Generate and set system instructions using an LLM and a task. This function will generate the system
        instructions and also set it as the system instructions for the moderator.

        Args:
            task (str): The task description.
            max_tries (int, optional): The maximum number of attempts to generate valid system instructions. Default is 10.

        Returns:
            System instructions for the moderator.

        Sets:
            system_instructions (str): The system instructions for the moderator.
        """
        self.system_instructions = self.generate_system_instructions(task, max_tries)
        return self.system_instructions

    def _moderate_responses(self, responses: List[str], original_task: str) -> str:
        """
        Combine responses using the moderator persona and instructions.

        Args:
            responses (List[str]): List of responses from agents to combine.
            original_task (str): The original task description provided to the agents.

        Returns:
            str: A combined response based on the moderator's instructions
        """
        combined_responses_str = format_previous_responses(responses)
        self.combination_instructions = SmartString(self.combination_instructions).format(
            previous_responses=combined_responses_str,
            task=original_task,
            avoid_double_period=True
        )
        self.system_instructions = SmartString(self.system_instructions).format(
            task=original_task,
            previous_responses=combined_responses_str,
            persona=self.persona
        )
        return self.process(previous_responses=combined_responses_str)


class AbstractStructure(ABC):
    """
    AbstractStructure is an abstract class for processing tasks through a group of agents. As such, it is not meant
    to be instantiated directly but rather to be subclassed by concrete structures such as an Ensemble. However,
    all the concrete structures share the same attributes and methods, so this class provides a common interface.

    Args:
        agents (List[Agent]): A list of agents to include in the structure.
        task (Optional[str]): The task description for the agents to process.
        shuffle (bool): Whether to shuffle the order of the agents.
        cycles (int): The number of times to process the task.
        last_n (int): The number of previous responses to include in the task description.
        combination_instructions (Optional[str]): The instructions for combining responses.
        moderator (Optional[Moderator]): A moderator to moderate the responses.

    Attributes:
        defaults (Dict[str, Any]): Default instructions for the structure.
        task (Optional[str]): The task description for the agents to process.
        agents (List[Agent]): A list of agents to include in the structure.
        combination_instructions (str): The instructions for combining responses.
        shuffle (bool): Whether to shuffle the order of the agents.
        last_n (int): The number of previous responses to include in the task description.
        cycles (int): The number of times to process the task.
        responses (List[str]): A list of responses from the agents.
        final_response (Optional[str]): The final response from the agents.
        moderator (Optional[Moderator]): A moderator to moderate the responses.
        moderated (bool): Whether the structure is moderated.
    """

    def __init__(
            self,
            agents: List[Agent],
            task: Optional[str] = None,
            shuffle: bool = False,
            cycles: int = 1,
            last_n: int = 1,
            combination_instructions: Optional[str] = "default",
            moderator: Optional[Moderator] = None):

        self.defaults = DEFAULTS
        self.task = task

        if not agents:
            raise ValueError("Agent list cannot be empty.")
        self.agents = agents

        self.combination_instructions = combination_instructions
        self._set_combination_instructions()
        self._set_task_descriptions()

        if not isinstance(shuffle, bool):
            raise ValueError("Shuffle must be a boolean.")
        self.shuffle = shuffle

        if not isinstance(cycles, int) or cycles < 1:
            raise ValueError("Cycles must be a positive integer.")
        self.cycles = cycles

        if not isinstance(last_n, int) or last_n < 1:
            raise ValueError("Last_n must be a positive integer.")
        self.last_n = last_n

        self.responses = []
        self.final_response = None
        self.moderator = moderator
        self.moderated = True if moderator else False

        # If we have a moderator we assign a task description and then we
        # populate the templates
        if self.moderator:
            if self.moderator.system_instructions == 'auto':
                self.moderator.system_instructions = self.moderator.generate_system_instructions(
                    self.task)
            self.moderator.task_description = self.task
            self.moderator.persona = SmartString(
                self.moderator.persona).format(
                task=self.task) if self.moderator.persona else None

        if shuffle:
            self.agents = random.sample(self.agents, len(self.agents))

    def _set_combination_instructions(self) -> None:
        """
        Set the combination instructions for agents based on the provided value or the default.
        """
        self.combination_instructions = SmartString(
            self.defaults['combination_instructions'].get(
                self.combination_instructions,
                self.combination_instructions))

        for agent in self.agents:
            if agent.combination_instructions:
                warnings.warn(
                    "Writing over agent's combination instructions with Chain's combination instructions")
            else:
                pass
            agent.combination_instructions = self.combination_instructions

    def _set_task_descriptions(self) -> None:
        """
        Set the task description for agents based on the provided value or the default.

        Logic:
            - Case 1: Value provided to both chain and agents--overwrite agent's task description with chain's task
            description and throw a warning to user.
            - Case 2: Value provided to chain but not agents--set agent's task description to be agent's task
            description.
            - Case 3: Value provided to neither agents nor chain: Throw an error
        """
        for agent in self.agents:
            if not self.task:
                if not agent.task_description or agent.task_description.strip() == '':
                    raise ValueError(
                        "Error: You did not specify a task for agents or chain")
            else:
                if agent.task_description:
                    warnings.warn(
                        "Writing over agent's task with Chain's task")
                agent.task_description = self.task
                agent.original_task_description = agent.task_description
                agent.system_instructions = SmartString(
                    agent.system_instructions).format(
                    task=self.task)

    @property
    def info(self) -> Dict[str, Any]:
        """
        Return information about the structure and its agents.
        """
        if not self.final_response:
            warnings.warn(
                "The structure has not been processed yet so there are no responses.")
        result = {
            "structure_information": {
                "final_response": self.final_response,
                "responses": self.responses,
                "task": self.task,
                "combination_instructions": self.combination_instructions,
                "moderated": self.moderated,
                "moderator_persona": self.moderator.persona if self.moderator else None,
                "moderator_instructions": self.moderator.combination_instructions if self.moderator else None
            },
            "agent_information": [agent.info for agent in self.agents]
        }
        return result

    @abstractmethod
    def process(self) -> None:
        """
        Abstract method for processing agents. Must be implemented in a subclass.
        """
        raise NotImplementedError(
            "This method must be implemented in a subclass")

    def __repr__(self):
        return str(self.info)


# Concrete Structures
#########################################################################
#########################################################################
class Chain(AbstractStructure):
    """
    A chain structure for processing tasks through a sequence of agents. In a chain,
    each agent processes the task after seeing a prior agent's response.

    **Examples:**
        **Using Chain to create a panel of agents that process tasks in a sequence:**

        .. code-block:: python

           agent1 = Agent(persona='a liberal woman from Missouri', model='gpt-4o')
           agent2 = Agent(persona='a 24 year old hispanic man from Florida', model='gpt-4o')
           agent3 = Agent(persona='an elderly woman with a PhD', model='gpt-4o')

           chain = Chain([agent1, agent2, agent3],
              task="How should we combat climate change?",
              combination_instructions="chain")
           chain.process()
           print(chain.final_response)
    """

    def process(self):
        """
        Process the task through a chain of agents, each building upon the last. Use parameters from
        `AbstractStructure` to control how the chain operates (e.g: last_n for how many previous responses to include
        in the `previous_responses` string)
        """
        previous_responses = []
        original_task = self.agents[0].original_task_description
        for _ in range(self.cycles):
            if self.shuffle:
                self.agents = random.sample(self.agents, len(self.agents))
            for agent in self.agents:
                previous_responses_slice = previous_responses[-self.last_n:]
                previous_responses_str = format_previous_responses(previous_responses_slice)
                agent.combination_instructions = self.combination_instructions
                response = agent.process(
                    previous_responses=previous_responses_str)
                previous_responses.append(response)
                self.responses.append(response)

        if self.moderated and self.moderator:
            moderated_response = self.moderator._moderate_responses(self.responses, original_task)
            self.responses.append(moderated_response)
        self.final_response = self.responses[-1]


class Ensemble(AbstractStructure):
    """
    An ensemble structure for processing tasks through a group of agents. In an ensemble, each agent processes the
    task independently through async requests.

    **Examples:**
        **Using Ensemble to brainstorm ideas:**

        .. code-block:: python

            task = "Brainstorm ideas to improve America."
            agents = [Agent(persona='random', model='gpt-4o') for i in range(10)] # random ANES agents
            moderator = Moderator(persona='default', model='gpt-4o') # default moderator persona
            ensemble = Ensemble(agents, moderator=moderator, task=task)
            ensemble.process()
            print(ensemble.final_response)
    """

    def process(self):
        """
        Requests are sent to all agents simultaneously.
        """
        original_task = self.agents[0].original_task_description
        for _ in range(self.cycles):
            with ThreadPoolExecutor() as executor:
                futures = []
                for agent in self.agents:
                    previous_responses_str = ""
                    agent.combination_instructions = self.combination_instructions
                    futures.append(executor.submit(agent.process, previous_responses=previous_responses_str))
                for future in as_completed(futures):
                    response = future.result()
                    self.responses.append(response)

        if self.moderated and self.moderator:
            moderated_response = self.moderator._moderate_responses(
                self.responses, original_task)
            self.responses.append(moderated_response)
        self.final_response = self.responses[-1]


class Debate(AbstractStructure):
    """
    In a debate, two agents take turns responding to a task, with each response building upon the previous one.
    Debate differs from other structures in a few key ways:

    1. It requires exactly two agents.
    2. It alternates between agents for each response, and prefixes each response with `[You]:` or `[Other]:` to
       indicate the speaker.
    3. When moderated, the moderator will provide a final response based on the debate, and we will append
       `[Debater 1]` and `[Debater 2]` to the responses so that the moderator is aware of who said what.

    **Examples:**
        **Using Debate to observe a conservative vs. a liberal viewpoint:**

        .. code-block:: python

            task = 'To what extent should the government be involved in providing free welfare to citizens?'
            agent1 = Agent(persona="a liberal", persona_template="default", model='gpt-4o')
            agent2 = Agent(persona="a conservative", persona_template="default", model='gpt-4o')
            moderator = Moderator(persona='You are a neutral moderator overseeing this task, ${task}', model='gpt-4o', combination_instructions="default")

            debate = Debate([agent1, agent2], task=task,  combination_instructions="debate", moderator=moderator)
            debate.process()
            print(debate.final_response)
    """

    def __init__(
            self,
            agents: List[Agent],
            task: Optional[str] = None,
            shuffle: bool = False,
            cycles: int = 1,
            last_n: int = 1000000,
            combination_instructions: Optional[str] = "debate",
            moderator: Optional[Moderator] = None):
        if len(agents) != 2:
            raise ValueError("Debate requires exactly two agents.")
        super().__init__(
            agents,
            task,
            shuffle,
            cycles,
            last_n,
            combination_instructions,
            moderator)

    @staticmethod
    def _format_previous_responses(responses: List[str]) -> str:
        """
        We don't need to append [Response 0] and [Response 1] to the responses here because they will be prefixed
        with [You] and [Other] in the process method already.

        Returns:
            str: The formatted responses newline seperated
        """
        if not responses:
            return ""
        else:
            resp_list = [
                "\n{}".format(
                    responses[i]) for i in range(
                    len(responses))]
            return "".join(resp_list).strip()

    def process(self):
        """
        Process the debate. In a debate, two agents take turns responding to a task. Prompts for agents are prefixed
        with [You] and [Other] to indicate the speaker. For moderators the responses are prefixed with [Debater 1] and
        [Debater 2] to indicate the speaker.
        """


        # Initialize lists for storing responses from the perspective of each agent.
        # This is necessary for the debate structure because each agent needs to see which is there's and which is
        # the other agent's response.
        #
        # This structure (of storing seperate lists) is useful since we need to return an agent's history of what
        # they saw, but there may be a more elegant way to do this.

        previous_responses_agent1 = []
        previous_responses_agent2 = []
        original_task = self.agents[0].original_task_description

        for cycle in range(self.cycles):
            for i, agent in enumerate(self.agents):
                # Choose the appropriate response history based on the agent
                # index
                if i == 0:
                    previous_responses_str = self._format_previous_responses(
                        previous_responses_agent1[-self.last_n:])
                else:
                    previous_responses_str = self._format_previous_responses(
                        previous_responses_agent2[-self.last_n:])

                agent.combination_instructions = self.combination_instructions
                response = agent.process(
                    previous_responses=previous_responses_str)
                self.responses.append("[Debater {}] ".format(i + 1) + response)

                # Apply the correct prefix and update both lists
                if i == 0:
                    previous_responses_agent1.append(f"[You]: {response}")
                    previous_responses_agent2.append(f"[Other]: {response}")
                else:
                    previous_responses_agent2.append(f"[You]: {response}")
                    previous_responses_agent1.append(f"[Other]: {response}")

        if self.moderated and self.moderator:
            moderated_response = self.moderator._moderate_responses(
                self.responses, original_task)
            self.responses.append(moderated_response)
        self.final_response = self.responses[-1]
