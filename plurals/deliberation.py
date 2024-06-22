from typing import List, Optional, Dict, Any
import random
import warnings
from plurals.agent import Agent
from plurals.helpers import load_yaml, format_previous_responses

DEFAULTS = load_yaml("instructions.yaml")


class Moderator(Agent):
    def __init__(self, moderator_config: Optional[Dict[str, Any]] = None, agents: Optional[List[Agent]] = None,
                 task: Optional[str] = None):
        """
        Initialize the moderator with specific configurations.

        Args:
            moderator_config (Optional[Dict[str, Any]]): Configuration for the moderator including
                                                         'persona', 'instructions', and 'model'.
            agents (Optional[List[Agent]]): List of agents in the chain to derive defaults if needed.
            task (Optional[str]): The task description to personalize the moderator's persona and instructions.
        """
        self.moderator_config = moderator_config
        if not moderator_config:
            self.moderator_config = {'persona': 'default', 'instructions': 'default', 'model': 'gpt-4o'}

        self.validate()
        model = self.moderator_config.get('model', agents[0].model)
        persona = self.get_persona(self.moderator_config.get('persona'))
        combination_instructions = self.get_instructions(self.moderator_config.get('instructions'))

        # Perform string replacements for placeholders, integrating task description
        persona = persona.replace("{task}", task)
        combination_instructions = combination_instructions.replace("{task}", task)

        super().__init__(task_description=task or "", model=model, persona=persona)
        self.combination_instructions = combination_instructions

    def get_persona(self, given_persona: str) -> str:
        """
        Retrieve the moderator's persona from the configuration or defaults.

        Args:
            given_persona (str): Persona is passed directly or it's a key to lookup
        """
        return DEFAULTS['moderator']['persona'].get(given_persona, given_persona)

    def get_instructions(self, given_instructions: str) -> str:
        """
        Retrieve the moderator's instructions from the configuration or defaults.

        Args:
            given_instructions (str): Instructions is passed directly or it's a key to lookup
        """
        return DEFAULTS['moderator']['instructions'].get(given_instructions, given_instructions)

    def validate(self):
        """
        Validate the moderator's configuration, ensuring no unexpected keys are present.
        """
        allowed_keys = {'persona', 'instructions', 'model'}
        if not set(self.moderator_config.keys()).issubset(allowed_keys):
            raise ValueError(
                "Invalid keys in moderator config. Allowed options are 'persona', 'instructions', 'model'.")

    def moderate_responses(self, responses: List[str]) -> str:
        """
        Combine responses using the moderator persona and instructions.

        Args:
            responses (List[str]): List of responses from agents to combine.

        Returns:
            str: A combined response based on the moderator's instructions and persona.
        """
        combined_responses = format_previous_responses(responses)
        return self.process_task(previous_responses=combined_responses)


class Chain:
    def __init__(self, agents: List[Agent],
                 task_description: Optional[str] = None,
                 shuffle: bool = False, cycles: int = 1, last_n: int = 1,
                 moderated: Optional[bool] = None, moderator_config: Optional[Dict[str, Any]] = None,
                 combination_instructions: Optional[str] = "default"):
        """
        Initialize a chain with a list of agents.

        Args:
            agents (List[Agent]): List of agents participating in the chain.
            shuffle (bool): Whether to shuffle the order of agents.
            cycles (int): Number of cycles of interaction.
            last_n (int): Number of previous responses to consider.
            moderated (Optional[bool]): Whether to use a moderator.
            moderator_config (Optional[Dict[str, Any]]): Configuration for the moderator.
        """

        self.agents = random.sample(agents, len(agents)) if shuffle else agents
        self.task_description = task_description
        self.cycles = cycles
        self.last_n = last_n
        self.responses = []
        self.combination_instructions = self.get_combination_instructions(combination_instructions)
        self.moderated = moderated or bool(moderator_config)
        self.set_task_descriptions()
        self.moderator = Moderator(moderator_config, agents, task_description) if self.moderated else None


    def process_chain(self):
        """
        Process the task through a chain of agents, each building upon the last.
        """
        previous_responses = []
        original_task = self.task_description or "No task specified"
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

    def get_combination_instructions(self, given_instructions: str) -> str:
        """
        Resolve the combination instructions from a default set or a specified key.

        Args:
            given_instructions (str): The key to lookup in the defaults for instructions.

        Returns:
            str: The combination instructions resolved from defaults or directly used.
        """
        return DEFAULTS['combination_instructions'].get(given_instructions, given_instructions)

    def set_task_descriptions(self):
        """
        Ensure all agents have an appropriate task description, falling back to the chain's description if needed.
        """
        if not self.task_description:
            raise ValueError("A task description must be provided if none is set for the agents.")

        for agent in self.agents:
            agent_original_task = getattr(agent, 'task_description')
            if agent_original_task:
                warnings.warn("Overriding agent's task description with Chain's task.")
            agent.task_description = self.task_description
