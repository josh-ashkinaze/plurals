from plurals.agent import Agent
from plurals.helpers import load_yaml, format_previous_responses
import os
from typing import Optional, Dict, Any, List
import random
import warnings

DEFAULTS = load_yaml("instructions.yaml")


class Moderator(Agent):
    def __init__(self, persona: str = "default", instructions: str = "default", model: str = "gpt-4"):

        """
        Initialize the moderator with specific configurations.

        Args:
            persona: The persona to use for the moderator.
            instructions: The instructions to combine the final responses
            model: The model to use for the moderator.
        """

        # Agent requires system instructions to be set, which for Agent is the prefix_template and the persona
        # but for the moderator, we just want the persona.
        self.defaults = DEFAULTS
        self.system_instructions = self.get_persona(persona)
        self.combination_instructions = self.get_instructions(instructions)
        self.model = model
        super().__init__(model=model, system_instructions=self.system_instructions)


    def get_persona(self, persona: str) -> str:
        """
        Retrieve the moderator's persona from the configuration or defaults.
        """
        return self.defaults['moderator']['persona'].get(persona, persona)

    def get_instructions(self, instructions: str) -> str:
        """
        Retrieve the moderator's instructions from the configuration or defaults.
        """
        return self.defaults['moderator']['combination_instructions'].get(instructions, instructions)

    def inherit_chain_attributes(self, task: str):
        """
        Set the task description for the moderator from the Chain.
        """
        self.original_task_description = task
        self.combination_instructions = self.combination_instructions.replace("{task}", task)
        self.system_instructions = self.system_instructions.replace("{task}", task)

    def moderate_responses(self, previous_responses: str) -> str:
        """
        Combine the previous responses from the chain into a final response.
        """
        return self.process_task(previous_responses)

    def validate(self):
        """
        Validate the moderator's configuration.
        """
        assert self.system_instructions, "Error: Moderator requires system instructions to be set."
        assert self.combination_instructions, "Error: Moderator requires combination instructions to be set."



class Chain:
    def __init__(self, agents: List[Agent],
                 task_description: Optional[str] = None,
                 shuffle: bool = False, cycles: int = 1, last_n: int = 1,
                 moderated: Optional[bool] = None,
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
        self.moderated = moderated
        self.moderator = moderator
        self.task_description = task_description
        self.agents = agents
        self.combination_instructions = combination_instructions
        self.set_combination_instructions()
        self.set_task_descriptions()
        self.set_moderator_properties()
        self.shuffle = shuffle
        self.last_n = last_n
        self.cycles = cycles
        self.responses = []
        self.moderated = moderated
        self.moderator = moderator
        self.final_response = None

        if shuffle: self.agents = random.sample(self.agents, len(self.agents))

    def process_chain(self):
        """
        Process the task through a chain of agents, each building upon the last.
        """
        previous_responses = []
        original_task = self.agents[0].original_task_description if self.agents else "No task given"
        print ("ORIGINAL")
        print (original_task)
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

    def set_combination_instructions(self):
        """
        Set the combination instructions for agents based on the provided value or the default.
        """

        # If the combination option is one in the yaml file, we set that, otherwise we use the provided value
        self.combination_instructions = self.defaults['combination_instructions'].get(self.combination_instructions, self.combination_instructions)

        # Set combo instructions for agents
        for agent in self.agents:
            if agent.combination_instructions: warnings.warn("Writing over agent's combination instructions with Chain's combination instructions")
            agent.combination_instructions = self.combination_instructions

    def set_task_descriptions(self):
        """
        Set the task description for agents based on the provided value or the default.

        If no task description is provided to the chain, then one must be provided to the agents or else an error is thrown.

        If a task description is provided to both agents and the chain, then we over-write the agents task description and raise a warning.
        """

        for agent in self.agents:
            if not self.task_description:
                if not agent.task_description or agent.task_description.strip() == '':
                    assert False, "Error: You did not specify a task for agents or chain"
            else:
                if agent.task_description:
                    warnings.warn("Writing over agent's task with Chain's task")
                agent.task_description = self.task_description
                agent.original_task_description = agent.task_description

    def set_moderator_properties(self):
        """
        If moderated is True but none is set, we use default moderator.

        Then we pass in task of chain to the moderator.
        """
        if self.moderated and not self.moderator:
            self.moderator = Moderator()
        self.moderated = True if self.moderator else False
        if self.moderated:
            self.moderator.inherit_chain_attributes(self.task_description)


