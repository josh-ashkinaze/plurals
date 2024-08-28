from typing import List, Optional, Dict, Any
import random
import warnings
from plurals.agent import Agent
from plurals.helpers import load_yaml, format_previous_responses
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from plurals.helpers import SmartString, strip_nested_dict
import re
import collections
from pprint import pprint

DEFAULTS = load_yaml("instructions.yaml")
DEFAULTS = strip_nested_dict(DEFAULTS)


class Moderator(Agent):
    """
    A moderator agent that combines responses from other agents at the end of structure processing.

    Args:
        persona (str, optional): The persona of the moderator. Default is 'default'. The persona can take in a ${task} placeholder.
        system_instructions (str, optional): The system instructions for the moderator. Default is None. If you pass in
            'auto', an LLM will generate its own system instructions automatically based on the task.
            ``system_instructions`` can take in a ${task} placeholder. If you use ``system_instructions``,
            you cannot use ``persona`` since that is an
            alternative way to set the system instructions.
        combination_instructions (str, optional): The instructions for combining responses. Default is 'default'. The combination instructions can take in a ${previous_responses} placeholder.
        model (str, optional): The model to use for the moderator. Default is 'gpt-4o'.
        task (str, optional): The task description for the moderator. By default, moderators will inherit the task
            from the Structure so this can be left blank. It is only required in a specific case: you wish to manually generate system
            instructions outside of the Structure. Note that if you use auto-mods inside of the Structure, the task will be inherited from the Structure.
        kwargs (Optional[Dict]): Additional keyword arguments. These are from LiteLLM's completion function.
            (see here: https://litellm.vercel.app/docs/completion/input)

    Attributes:
        persona (str): The persona of the moderator.
        combination_instructions (str): The instructions for combining responses.
        system_instructions (str): The full system instructions for the moderator.


    **Examples**

        **Standard Usage: Inherit task from Structure**

        The standard usage is for the Moderator to inherit the task from the Structure. Here, the system instructions will replace the ${task} placeholder in the `default` Moderator template.

        .. code-block:: python

            # Example 1
            task = "What are your thoughts on the role of government in society? Answer in 20 words."
            # Uses templates for personas and combination instructions
            moderator = Moderator(persona='default', model='gpt-4o', combination_instructions='default')
            agent1 = Agent(model='gpt-3.5-turbo')
            agent2 = Agent(model='gpt-3.5-turbo')
            chain = Chain([agent1, agent2], moderator=moderator, task=task)
            chain.process()

            # Example 2
            task = "What are your thoughts on the role of government in society? Answer in 10 words."
            moderator = Moderator(
                persona="You are an expert overseeing a discussion about ${task}",
                model='gpt-4o',
                combination_instructions="Come to a final conclusion based on previous responses: $previous_responses"
            )
            agent1 = Agent(model='gpt-3.5-turbo')
            agent2 = Agent(model='gpt-3.5-turbo')
            chain = Chain([agent1, agent2], moderator=moderator, task=task)
            chain.process()

        **Alternatively, you can set the system instructions directly.**

        .. code-block:: python

            moderator = Moderator(
                system_instructions='Summarize previous responses as neutrally as possible.',
                model='gpt-4o',
                combination_instructions='second_wave'
            )

        **Auto-Moderator: Declared inside of Structure**

        If the ``system_instructions`` of a moderator are set to 'auto', then the moderator will, given a task, come up with its own system instructions. Here the task is inherited from the Structure.

        .. code-block:: python

            task = ("Your goal is to come up with the most creative ideas possible for pants. We are maximizing creativity. Answer"
                    " in 20 words.")
            a = Agent(model='gpt-4o')
            b = Agent(model='gpt-3.5-turbo')
            chain = Chain([a, b], moderator=Moderator(system_instructions='auto', model='gpt-4o'), task=task)
            chain.process()
            print(chain.moderator.system_instructions)

        Output:

        .. code-block:: text

            Group similar ideas together, prioritize uniqueness and novelty. Highlight standout concepts and remove
            duplicates. Ensure the final list captures diverse and imaginative designs.

        **Auto-Moderator: Declared outside of Structure**

        Here we use an auto-moderator again, but this time the auto-moderated system instructions come from a different
        task than what Agents complete.

        .. code-block:: python

            moderator_task = "What is a creative use for pants?"
            moderator = Moderator(system_instructions='auto', model='gpt-4o', task=task)
            a1 = Agent(model='gpt-4o-mini')
            a2 = Agent(model='gpt-4o-mini')
            chain = Chain([a1, a2], moderator=moderator, task=task)
            chain.process()
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

        self.task = task

        if system_instructions is not None and system_instructions != 'auto':
            if "${task}" not in system_instructions:
                warnings.warn(
                    "System instructions usually contain the placeholder ${task} so Moderators know what task it is. Consider adding 'Here is the task: ${task}' to your system instructions.")

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
            super().__init__(persona=persona_value, persona_template=persona_template, model=model, kwargs=kwargs,
                             task=task)

        # Case 4: if only system_instructions is provided, set system_instructions and set persona and persona_template to None
        elif system_instructions and not persona:
            super().__init__(system_instructions=system_instructions, persona=None, persona_template=None, model=model,
                             kwargs=kwargs, task=task)

        # Case 5: if neither persona nor system_instructions are provided, set no system instructions.
        else:
            super().__init__(system_instructions=None, model=model, kwargs=kwargs,
                             task=task)

        self.combination_instructions = DEFAULTS["moderator"]['combination_instructions'].get(combination_instructions,
                                                                                              combination_instructions)

    def generate_system_instructions(self, task: str, max_tries: int = 10) -> str:
        """
        Generate and instructions using an LLM and a task. This function will not automatically set the system
        instructions, but it will return the generated system instructions (so you can inspect or re-generate them).
        Then you can set system instructions using the ``system_instructions`` attribute.

        See ``generate_and_set_system_instructions`` for a function that will generate and set the system instructions.

        Args:
            task (str): The task description for which system instructions need to be generated.
            max_tries (int): The maximum number of attempts to generate valid system instructions. Default is 10.

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

    def _moderate_responses(self, responses: List[str]) -> str:
        """
        Combine responses using the moderator persona and instructions.

        Args:
            responses (List[str]): List of responses from agents to combine.

        Returns:
            str: A combined response based on the moderator's instructions
        """
        print("task", self.task)
        combined_responses_str = format_previous_responses(responses)
        self.combination_instructions = SmartString(self.combination_instructions).format(
            previous_responses=combined_responses_str,
            task=self.task,
            avoid_double_period=True
        )
        if self.system_instructions:
            self.system_instructions = SmartString(self.system_instructions).format(
                task=self.task,
                previous_responses=combined_responses_str,
                persona=self.persona
            )
        else:
            pass

        return self.process(previous_responses=combined_responses_str)


class AbstractStructure(ABC):
    """
    AbstractStructure is an abstract class for processing tasks through a group of agents. As such, it is not meant
    to be instantiated directly but rather to be subclassed by concrete structures such as an Ensemble. However,
    all the concrete structures share the same attributes and methods, so this class provides a common interface.

    Args:
        agents (List[Agent]): A list of agents to include in the structure.
        task (Optional[str]): The task description for the agents to process.
        shuffle (bool): Whether to shuffle the order of the agents. Default is False.
        cycles (int): The number of times to process the task. Default is 1.
        last_n (int): The maximum number of previous responses each Agent has access to. Default is 1000.
        combination_instructions (Optional[str]): The instructions for combining responses. The default is the
        `default`
        template.
        moderator (Optional[Moderator]): A moderator to moderate the responses. The default is None.

    Attributes:
        defaults (Dict[str, Any]): A dict corresponding the YAML file of templates.
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
            last_n: int = 1000,
            combination_instructions: Optional[str] = "default",
            moderator: Optional[Moderator] = None):

        self.defaults = DEFAULTS
        self.task = task

        if not agents:
            raise ValueError("Agent list cannot be empty.")
        self.agents = agents

        self.combination_instructions = combination_instructions
        self._set_combination_instructions()
        self._set_agent_task_description()

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
            self._set_moderator_task_description()
            if self.moderator.system_instructions == 'auto':
                self.moderator.system_instructions = self.moderator.generate_system_instructions(
                    self.moderator.task)
            self.moderator.task_description = self.task
            self.moderator.persona = SmartString(
                self.moderator.persona).format(
                task=self.moderator.task) if self.moderator.persona else None

        if shuffle:
            self.agents = random.sample(self.agents, len(self.agents))

    def _set_combination_instructions(self) -> None:
        """
        Set the combination instructions for agents based on the provided value or the default. If agents have their own
        combination instructions, use those instead.

        """
        self.combination_instructions = SmartString(
            self.defaults['combination_instructions'].get(
                self.combination_instructions,
                self.combination_instructions))

        for agent in self.agents:
            if agent.combination_instructions:
                pass
            else:
                agent.combination_instructions = self.combination_instructions

    def _set_agent_task_description(self) -> None:
        """
        Set the task description for agents based on the provided value or the default.

        Logic:
            - Case 1: Task provided to both Structure and agents--use agent's task description but throw a warning to user.
            - Case 2: Value provided to neither agents nor chain: Raise an error.
            - Case 3: Value provided to Structure but not agents--set agent's task description to be Structure's task
            description.
            - Case 4: Value provided to agents but not Structure. Use Agent's task description.
        """
        for agent in self.agents:
            if self.task:
                if agent.task_description:
                    # Case 1: Task provided to both Structure and agents
                    warnings.warn(
                        f"You provided a task to both the Structure and agents. Using agent's task description:'''\n\n{agent.task_description}'''\n\nEnsure this is what you want to happen.")
                    agent.task_description = self.task
                else:
                    # Case 3: Value provided to Structure but not agents
                    agent.task_description = self.task

                # Common operations for cases 1 and 3
                agent.original_task_description = agent.task_description
                agent.system_instructions = SmartString(
                    agent.system_instructions).format(task=self.task)
            else:
                if not agent.task_description or agent.task_description.strip() == '':
                    # Case 2: Value provided to neither agents nor chain
                    raise ValueError("Error: You did not specify a task for agents or chain")
                else:
                    # Case 4: Value provided to agents but not Structure
                    pass  # Use Agent's existing task description

    def _set_moderator_task_description(self) -> None:
        """
        Set the task description for Moderators.

        Logic:
            - Case 1: Task provided to both Structure and moderator--use moderator's task description but throw a warning to user.
            - Case 2: Value provided to neither moderator nor structure: Raise an error.
            - Case 3: Value provided to Structure but not moderator--set moderator's task description to be Structure's
            task description.
            - Case 4: Value provided to moderator but not Structure. Use Moderator's task description.
        """
        if self.moderator:
            if self.task:
                if self.moderator.task:
                    # Case 1: Task provided to both Structure and moderator
                    warnings.warn(
                        f"You provided a task to both the Structure and a Moderator. Using the Moderator's task description:'''\n\n{self.moderator.task}'''\n\nEnsure this is what you want to happen.")

                else:
                    # Case 3: Value provided to Structure but not moderator
                    self.moderator.task = self.task

                # Common operations for cases 1 and 3
                self.moderator.task_description = self.task
                self.moderator.system_instructions = SmartString(
                    self.moderator.system_instructions).format(task=self.task) if self.moderator.system_instructions else None
            else:
                if not self.moderator.task or self.moderator.task.strip() == '':
                    # Case 2: Value provided to neither moderator nor structure
                    raise ValueError("Error: You did not specify a task for Moderator or Structure")
                else:
                    # Case 4: Value provided to moderator but not Structure
                    pass  # Use Moderator's existing task description

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
        return pprint(self.info)


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
        `AbstractStructure` to control how the chain operates (e.g: ``last_n`` for how many previous responses to include
        in the `previous_responses` string)
        """
        previous_responses = []
        for _ in range(self.cycles):
            if self.shuffle:
                self.agents = random.sample(self.agents, len(self.agents))
            for agent in self.agents:
                agent.current_task_description = None
                previous_responses_slice = previous_responses[-self.last_n:]
                previous_responses_str = format_previous_responses(previous_responses_slice)
                agent.combination_instructions = self.combination_instructions
                response = agent.process(previous_responses=previous_responses_str)
                previous_responses.append(response)
                self.responses.append(response)

        if self.moderated and self.moderator:
            moderated_response = self.moderator._moderate_responses(self.responses)
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
                self.responses)
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
            last_n: int = 1000,
            combination_instructions: Optional[str] = "debate",
            moderator: Optional[Moderator] = None):
        if len(agents) != 2:
            raise ValueError("Debate requires exactly two agents.")
        super().__init__(
            agents,task,shuffle,cycles,last_n,combination_instructions,moderator)

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

    @staticmethod
    def _strip_placeholders(response: str) -> str:
        """
        Strip placeholders from the response. These placeholders are used to indicate the speaker in the debate, but
        sometimes LLMs add them to the response. This function removes them.
        """
        return response.replace("[WHAT YOU SAID]: ", "").replace("[WHAT OTHER PARTICIPANT SAID]: ", "")

    def process(self):
        """
        Process the debate. In a debate, two agents take turns responding to a task. Prompts for agents are prefixed
        with [WHAT YOU SAID] and [WHAT OTHER PARTICIPANT SAID] to indicate the speaker. For moderators the responses are
        prefixed with [Debater 1] and [Debater 2] to indicate the speaker.
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
                agent.current_task_description = None
                # Choose the appropriate response history based on the agent
                # index
                if i == 0:
                    previous_responses_str = self._format_previous_responses(
                        previous_responses_agent1[-self.last_n:])
                else:
                    previous_responses_str = self._format_previous_responses(
                        previous_responses_agent2[-self.last_n:])

                agent.combination_instructions = self.combination_instructions
                response = agent.process(previous_responses=previous_responses_str)
                response = self._strip_placeholders(response)
                self.responses.append("[Debater {}] ".format(i + 1) + response)

                # Apply the correct prefix and update both lists
                if i == 0:
                    previous_responses_agent1.append(f"[WHAT YOU SAID]: {response}")
                    previous_responses_agent2.append(f"[WHAT OTHER PARTICIPANT SAID]: {response}")
                else:
                    previous_responses_agent2.append(f"[WHAT YOU SAID]: {response}")
                    previous_responses_agent1.append(f"[WHAT OTHER PARTICIPANT SAID]: {response}")

        if self.moderated and self.moderator:
            moderated_response = self.moderator._moderate_responses(
                self.responses)
            self.responses.append(moderated_response)
        self.final_response = self.responses[-1]


class Graph(AbstractStructure):
    """
    Initializes a network where agents are processed according to a topologically-sorted directed acyclic graph (DAG).
    This Structure takes in ``agents`` and a structure-specific property called `edges`. We offer two
    ways to construct the graph, with examples of each method right below.

    Method 1:

    - ``agents`` is a list of Agent objects.
    - ``edges`` is a list of integer tuples (``src_idx``, ``dst_idx``).

    Method 2:

    - ``agents`` is a dictionary of Agent objects with keys as agent names.
    - ``edges`` is a list of string tuples (``src_agent_name``, ``dst_agent_name``).

    Note that the graph must be a directed acyclic graph (DAG) or else an error will be raised.


    **Examples:**

        **Method 1:**

        Suppose we have three Agents, and we want to create a graph where the output of the liberal is fed to both the conservative and libertarian.
        Then the output of the conservative is fed to the libertarian.

        .. code-block:: python

            Agents = [
                Agent(system_instructions="you are a liberal", model="gpt-3.5-turbo"),
                Agent(system_instructions="you are a conservative", model="gpt-3.5-turbo"),
                Agent(system_instructions="you are a libertarian", model="gpt-3.5-turbo")
            ]
            edges = [(0, 1), (0, 2), (1, 2)]
            # edges = (liberal -> conservative), (liberal -> libertarian), (conservative -> libertarian)
            task = "What are your thoughts on the role of government in society? Answer in 20 words."
            graph = Graph(agents=Agents, edges=edges, task=task)
            graph.process()

        **Method 2:**

        .. code-block:: python

            agents = {
                'liberal': Agent(system_instructions="you are a liberal", model="gpt-3.5-turbo"),
                'conservative': Agent(system_instructions="you are a conservative", model="gpt-3.5-turbo"),
                'libertarian': Agent(system_instructions="you are a libertarian", model="gpt-3.5-turbo")
            }
            edges = [('liberal', 'conservative'), ('liberal', 'libertarian'), ('conservative', 'libertarian')]
            task = "What are your thoughts on the role of government in society?"
            graph = Graph(agents=agents, edges=edges, task=task)
            graph.process()


    """

    def __init__(self,
                 agents: List[Agent],
                 edges: List[tuple],
                 task: Optional[str] = None,
                 last_n: int = 1000,
                 combination_instructions: Optional[str] = "default",
                 moderator: Optional[Moderator] = None):
        """
        Args:
            agents (Union[List[Agent], Dict[str, Agent]]): A list or dictionary of agents to be included in the structure.
            edges (List[Tuple[Union[int, str], Union[int, str]]]): A list of tuples representing directed edges between agents.
            task (Optional[str]): The task description for the agents to process.
            last_n (int, optional): The number of last responses to consider for processing tasks. Defaults to 1000.
            combination_instructions (str, optional): The instructions for combining responses. Defaults to 'default'.
            moderator (Moderator, optional): A moderator to moderate responses. Defaults to None.
        """

        self.original_agents = agents
        self.original_edges = edges

        self._validate_input_format(agents, edges)

        # Method 2: Convert the dictionary to a list of agents and a list of edges (src_idx, dest_idx) so it is
        # consistent with Method 1
        if isinstance(agents, dict):
            self.agents = list(agents.values())
            self.edges = []
            name2idx = {name: idx for idx, name in enumerate(agents.keys())}
            for src_agent_name, dst_agent_name in edges:
                src_idx = name2idx[src_agent_name]
                dst_idx = name2idx[dst_agent_name]
                self.edges.append((src_idx, dst_idx))
        # Method 1: Use the agents and edges as is.
        else:
            self.agents = agents
            self.edges = edges

        super().__init__(agents=self.agents, task=task, last_n=last_n,
                         combination_instructions=combination_instructions,
                         moderator=moderator)
        self._build_graph()

    def _build_graph(self):
        """
        Builds the graph from the agents and edges. Edges are defined using indices to reference agents.
        Initializes the graph and in-degree count for each agent. This is the first part of the topological sorting.
        """
        self.graph = {agent: [] for agent in self.agents}
        self.in_degree = {agent: 0 for agent in self.agents}
        for src_idx, dst_idx in self.edges:
            src_agent = self.agents[src_idx]
            dst_agent = self.agents[dst_idx]
            self.graph[src_agent].append(dst_agent)
            self.in_degree[dst_agent] += 1

    def process(self):
        """
        Processes the tasks within the network of agents, respecting the directed acyclic graph (DAG) structure. The order
        of agent deliberation is determined using Kahn's algorithm for topological sorting.

        Kahn's Algorithm:

        1. Initialize a queue with agents that have an in-degree of 0 (no dependencies).

        2. While the queue is not empty:

           a. Remove an agent from the queue and add this agent to the topological order.

           b. For each successor of this agent:

              i. Decrease the successor's in-degree by 1.

              ii. If the successor's in-degree becomes 0, add it to the queue.

        This method ensures that agents are processed in an order where each agent's dependencies are processed before the agent itself.

        Returns:
            str: The final response after all agents have been processed, and potentially moderated.

        Raises:
            ValueError: If a cycle is detected in the DAG, as this prevents valid topological sorting.
        """

        # Initialize the queue with agents that have in-degree 0
        zero_in_degree_queue = collections.deque([agent for agent in self.agents if self.in_degree[agent] == 0])
        topological_order = []

        # Kahn's Algorithm
        while zero_in_degree_queue:

            # Pop the agent with in-degree 0
            current_agent = zero_in_degree_queue.popleft()

            # Add the agent to the topological order
            topological_order.append(current_agent)

            # Decrease the in-degree of the popped Agent's successors
            # If the in-degree of a successor becomes 0, add it to the queue
            for successor in self.graph[current_agent]:
                self.in_degree[successor] -= 1
                if self.in_degree[successor] == 0:
                    zero_in_degree_queue.append(successor)

        if len(topological_order) != len(self.agents):
            raise ValueError("There is a cycle in the graph!!! This is not allowed in a DAG.")

        # Process agents according to topological order
        response_dict = {}
        for agent in topological_order:
            agent.combination_instructions = self.combination_instructions
            # Gather responses from all predecessors to form the input for the current agent
            previous_responses = [response_dict[pred] for pred in self.agents if agent in self.graph[pred]]
            previous_responses_str = format_previous_responses(previous_responses)
            response = agent.process(previous_responses=previous_responses_str)
            response_dict[agent] = response
            self.responses.append(response)

        # Handle the moderator if present
        if self.moderated and self.moderator:
            original_task = self.agents[0].original_task_description
            moderated_response = self.moderator._moderate_responses(list(response_dict.values()))
            self.responses.append(moderated_response)
            self.final_response = moderated_response
        self.final_response = self.responses[-1]
        return self.final_response

    @staticmethod
    def _validate_input_format(agents, edges):

        # Check #1: Check if agents and edges are in the correct format
        if isinstance(agents, list) and all(isinstance(agent, Agent) for agent in agents) and all(
                isinstance(edge, tuple) for edge in edges):
            pass
        elif isinstance(agents, dict) and all(isinstance(agent, Agent) for agent in agents.values()) and all(
                isinstance(edge, tuple) for edge in edges):
            pass
        else:
            raise ValueError("The agents and edges must be in the correct format. See the documentation for more "
                             "information. Either (Method 1) `agents` is a list of Agents and `edges` is a list of "
                             "tuples corresponding to the indices of agents, (src_idx, dest_idx). Or, (Method 2) "
                             "`agents` is a dictionary of Agents and edges is a list of tuples corresponding to the "
                             "names of agents (src_agent_name, dest_agent_name).")

        # If Method 1: Check if edge indices are within the range of agents
        if isinstance(agents, list):
            for src_idx, dst_idx in edges:
                if src_idx >= len(agents) or dst_idx >= len(agents):
                    raise ValueError("Edge indices must be within the range of agents.")
                if src_idx == dst_idx:
                    raise ValueError("Self loops are not allowed in the graph.")

        # If Method 2: Check if agent names in edges are keys in the agent dictionary
        if isinstance(agents, dict):
            agent_names = list(agents.keys())
            for src_agent_name, dst_agent_name in edges:
                if src_agent_name not in agent_names or dst_agent_name not in agent_names:
                    raise ValueError("Agent names in edges must be keys in the agent dictionary.")
