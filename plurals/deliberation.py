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
        persona (str): The persona of the moderator. View `instructions.yaml` YAML file for templates.
        combination_instructions (str): The instructions for combining responses. View `instructions.yaml` YAML file
        for templates.
        model (str): The model to use for the moderator.
        **kwargs (dict): Additional keyword arguments. These are from LiteLLM's completion function. (see here:
        https://litellm.vercel.app/docs/completion/input)

    Attributes:
        combination_instructions (str): The instructions for combining responses.
        system_instructions (str): For a Moderator, system instructions are just the persona.
    """

    def __init__(self, persona: str = 'default', combination_instructions: str = "default", model: str = "gpt-4o",
                 **kwargs):
        super().__init__(task="", model=model,
                         persona=DEFAULTS["moderator"]['persona'].get(persona, persona), persona_template="${persona}",
                         **kwargs)

        self.combination_instructions = (
            DEFAULTS["moderator"]['combination_instructions'].get(combination_instructions, combination_instructions))

    def _moderate_responses(self, responses: List[str], original_task: str) -> str:
        """
        Combine responses using the moderator persona and instructions.

        Args:
            responses (List[str]): List of responses from agents to combine.
            original_task (str): The original task description provided to the agents.

        Returns:
            str: A combined response based on the moderator's instructions and persona.
        """
        combined_responses_str = format_previous_responses(responses)
        self.combination_instructions = SmartString(self.combination_instructions).format(
            previous_responses=combined_responses_str, task=original_task)
        self.system_instructions = SmartString(self.system_instructions).format(task=original_task,
                                                                                previous_responses=combined_responses_str,
                                                                                persona=self.persona)
        return self.process(previous_responses=combined_responses_str)


class AbstractStructure(ABC):
    """
    AbstractStructure is an abstract class for processing tasks through a group of agents. As such, it is not meant
    to be
    instantiated directly but rather to be subclassed by concrete structures such as an Ensemble. However,
    all the concrete
    structures share the same attributes and methods, so this class provides a common interface.

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

    def __init__(self, agents: List[Agent], task: Optional[str] = None, shuffle: bool = False,
                 cycles: int = 1, last_n: int = 1, combination_instructions: Optional[str] = "default",
                 moderator: Optional[Moderator] = None):
        self.defaults = DEFAULTS
        self.task = task
        self.agents = agents
        self.combination_instructions = combination_instructions
        self._set_combination_instructions()
        self._set_task_descriptions()
        self.shuffle = shuffle
        self.last_n = last_n
        self.cycles = cycles
        self.responses = []
        self.final_response = None
        self.moderator = moderator
        self.moderated = True if moderator else False

        # If we have a moderator we assign a task description and then we populate the templates
        if self.moderator:
            self.moderator.task_description = self.task
            self.moderator.persona = SmartString(self.moderator.persona).format(task=self.task)

        if shuffle:
            self.agents = random.sample(self.agents, len(self.agents))

    def _set_combination_instructions(self) -> None:
        """
        Set the combination instructions for agents based on the provided value or the default.
        """
        self.combination_instructions = SmartString(
            self.defaults['combination_instructions'].get(self.combination_instructions, self.combination_instructions))

        for agent in self.agents:
            if agent.combination_instructions:
                warnings.warn("Writing over agent's combination instructions with Chain's combination instructions")
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
                    raise ValueError("Error: You did not specify a task for agents or chain")
            else:
                if agent.task_description:
                    warnings.warn("Writing over agent's task with Chain's task")
                agent.task_description = self.task
                agent.original_task_description = agent.task_description
                agent.system_instructions = SmartString(agent.system_instructions).format(task=self.task)

    @property
    def info(self) -> Dict[str, Any]:
        """
        Return information about the structure and its agents.
        """
        if not self.final_response:
            raise ValueError("The structure has not been processed yet. Call the process method first.")
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
        raise NotImplementedError("This method must be implemented in a subclass")


class Chain(AbstractStructure):
    """
    A chain structure for processing tasks through a sequence of agents. In a chain,
    each agent processes the task after seeing a prior agent's response.
    """

    def process(self):
        """
        Process the task through a chain of agents, each building upon the last. Use parameters from
        `AbstractStructure` to control
        how the chain operates (e.g: last_n for how many previous responses to include in the `previous_resonses`
        string)
        """
        previous_responses = []
        original_task = self.agents[0].original_task_description
        for _ in range(self.cycles):
            for agent in self.agents:
                previous_responses_slice = previous_responses[-self.last_n:]
                previous_responses_str = format_previous_responses(previous_responses_slice)
                agent.combination_instructions = self.combination_instructions
                response = agent.process(previous_responses=previous_responses_str)
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
            moderated_response = self.moderator._moderate_responses(self.responses, original_task)
            self.responses.append(moderated_response)
        self.final_response = self.responses[-1]


class Debate(AbstractStructure):
    """
    In a debate, two agents take turns responding to a task, with each response building upon the previous one.
    Debate differs
    from other structures in a few key ways:

    - It requires exactly two agents.
    - It alternates between agents for each response, and prefixes each response with "[You]:" or "[Other]:" to
    indicate
    the speaker.
    - When moderated, the moderator will provide a final response based on the debate and we will append [Debater 1]
    and [Debater 2] to the responses so that the moderator is aware of who said what.
    """

    def __init__(self, agents: List[Agent], task: Optional[str] = None, shuffle: bool = False,
                 cycles: int = 1, last_n: int = 1000000, combination_instructions: Optional[str] = "debate",
                 moderator: Optional[Moderator] = None):
        if len(agents) != 2:
            raise ValueError("Debate requires exactly two agents.")
        super().__init__(agents, task, shuffle, cycles, last_n, combination_instructions, moderator)

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
            resp_list = ["\n{}".format(responses[i]) for i in range(len(responses))]
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
        # they saw, but there may be a more way to achieve this functionality.

        previous_responses_agent1 = []
        previous_responses_agent2 = []
        original_task = self.agents[0].original_task_description

        for cycle in range(self.cycles):
            for i, agent in enumerate(self.agents):
                # Choose the appropriate response history based on the agent index
                if i == 0:
                    previous_responses_str = self._format_previous_responses(previous_responses_agent1[-self.last_n:])
                else:
                    previous_responses_str = self._format_previous_responses(previous_responses_agent2[-self.last_n:])

                agent.combination_instructions = self.combination_instructions
                response = agent.process(previous_responses=previous_responses_str)
                self.responses.append("[Debater {}] ".format(i + 1) + response)

                # Apply the correct prefix and update both lists
                if i == 0:
                    previous_responses_agent1.append(f"[You]: {response}")
                    previous_responses_agent2.append(f"[Other]: {response}")
                else:
                    previous_responses_agent2.append(f"[You]: {response}")
                    previous_responses_agent1.append(f"[Other]: {response}")

        if self.moderated and self.moderator:
            moderated_response = self.moderator._moderate_responses(self.responses, original_task)
            self.responses.append(moderated_response)
        self.final_response = self.responses[-1]
