from typing import List, Optional, Dict, Any
import random
import warnings
from plurals.agent import Agent
from plurals.helpers import load_yaml, format_previous_responses
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULTS = load_yaml("instructions.yaml")


class Moderator(Agent):
    def __init__(self, persona: str = 'default', combination_instructions: str = "default", model: str = "gpt-4o"):
        """
        Initialize the moderator with specific configurations or defaults.
        """
        super().__init__(task_description="", model=model,
                         persona=DEFAULTS["moderator"]['persona'].get(persona, persona))

        self.combination_instructions = (
            DEFAULTS["moderator"]['combination_instructions'].get(combination_instructions, combination_instructions))
        self.system_instructions = self.persona

    def moderate_responses(self, responses: List[str], original_task: str) -> str:
        """
        Combine responses using the moderator persona and instructions.

        Args:
            responses (List[str]): List of responses from agents to combine.
            original_task (str): The original task description provided to the agents.

        Returns:
            str: A combined response based on the moderator's instructions and persona.
        """
        combined_responses_str = format_previous_responses(responses)
        moderator_task = self.combination_instructions.format(previous_responses=combined_responses_str,
                                                              task=original_task)
        self.combination_instructions = moderator_task
        self.system_instructions = self.system_instructions.format(task=original_task)
        return self.process_task(previous_responses=combined_responses_str)


class AbstractPlural(ABC):
    def __init__(self, agents: List[Agent],
                 task_description: Optional[str] = None,
                 shuffle: bool = False, cycles: int = 1, last_n: int = 1,
                 combination_instructions: Optional[str] = "default",
                 moderator: Optional[Moderator] = None):
        """
        Initialize a chain with a list of agents.

        Args:,

            agents (List[Agent]): List of agents participating in the chain.
            shuffle (bool): Whether to shuffle the order of agents.
            cycles (int): Number of cycles of interaction.
            last_n (int): Number of previous responses to consider.
            moderated (Optional[bool]): Whether to use a moderator.
            moderator_config (Optional[Dict[str, Any]]): Configuration for the moderator.
        """

        self.defaults = DEFAULTS
        self.task_description = task_description
        self.agents = agents
        self.combination_instructions = combination_instructions
        self.set_combination_instructions()
        self.set_task_descriptions()
        self.shuffle = shuffle
        self.last_n = last_n
        self.cycles = cycles
        self.responses = []
        self.final_response = None
        self.moderator = moderator
        self.moderated = True if moderator else False
        if self.moderator:
            self.moderator.task_description = self.task_description  # it's important to call igt after chain properties are setup
            self.moderator.persona = self.moderator.persona.format(task=self.task_description)

        if shuffle:
            self.agents = random.sample(self.agents, len(self.agents))

    def set_combination_instructions(self):
        """
        Set the combination instructions for agents based on the provided value or the default.
        """

        # If the combination option is one in the yaml file, we set that, otherwise we use the provided value
        self.combination_instructions = self.defaults['combination_instructions'].get(
            self.combination_instructions, self.combination_instructions)

        for agent in self.agents:
            if agent.combination_instructions:
                warnings.warn("Writing over agent's combination instructions with Chain's combination instructions")
            else:
                pass
            agent.combination_instructions = self.combination_instructions

    def set_task_descriptions(self):
        """
        Set the task description for agents based on the provided value or the default.

        If no task description is provided to the chain, then one must be provided to the agents or else an error is thrown.

        If a task description is provided to both agents and the chain, then we over-write the agents task description and raise a warning.
        """
        # E.F. Because we finalize the task in chain we have to keep the following here and not in Agent
        for agent in self.agents:
            if not self.task_description:
                if not agent.task_description or agent.task_description.strip() == '':
                    assert False, "Error: You did not specify a task for agents or chain"
            else:
                if agent.task_description:
                    warnings.warn("Writing over agent's task with Chain's task")
                agent.task_description = self.task_description
                agent.original_task_description = agent.task_description


class Chain(AbstractPlural):
    def process(self):
        """
        Process the task through a chain of agents, each building upon the last.
        """
        previous_responses = []
        original_task = self.agents[0].original_task_description
        for _ in range(self.cycles):
            for agent in self.agents:
                previous_responses_slice = previous_responses[-self.last_n:]
                previous_responses_str = format_previous_responses(previous_responses_slice)
                agent.combination_instructions = self.combination_instructions
                response = agent.process_task(previous_responses_str)
                previous_responses.append(response)
                self.responses.append(response)

        if self.moderated and self.moderator:
            moderated_response = self.moderator.moderate_responses(self.responses, original_task)
            self.responses.append(moderated_response)
        self.final_response = self.responses[-1]


class Ensemble(AbstractPlural):
    def process(self):
        """
        Process the tasks in parallel through a group of agents, each working independently.
        """
        original_task = self.agents[0].original_task_description
        for _ in range(self.cycles):
            with ThreadPoolExecutor() as executor:
                futures = []
                for agent in self.agents:
                    previous_responses_str = ""
                    agent.combination_instructions = self.combination_instructions
                    futures.append(executor.submit(agent.process_task, previous_responses_str))
                for future in as_completed(futures):
                    response = future.result()
                    self.responses.append(response)

        if self.moderated and self.moderator:
            moderated_response = self.moderator.moderate_responses(self.responses, original_task)
            self.responses.append(moderated_response)
        self.final_response = self.responses[-1]