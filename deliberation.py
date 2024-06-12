from typing import List, Optional, Dict, Any
import random
from .agent import Agent
from .helpers import load_yaml, format_previous_responses


class Moderator(Agent):
    def __init__(self, moderator_config: Optional[Dict[str, Any]] = None, agents: Optional[List[Agent]] = None):
        """
        Initialize the moderator with specific configurations or defaults.

        Args:
            moderator_config (Optional[Dict[str, Any]]): Configuration for the moderator that might include
                                                         'persona', 'combination_instructions', and 'model'.
            agents (Optional[List[Agent]]): List of agents in the chain to derive defaults if needed.
        """
        instructions = load_yaml("instructions.yaml")
        if moderator_config is None:
            moderator_config = {}

        original_task = agents[0].original_task_description if agents else "No task provided"

        persona = moderator_config.get('persona') or instructions['moderator']['persona']
        combination_instructions = moderator_config.get('instructions') or instructions['moderator']['instructions']
        model = moderator_config.get('model') or (agents[0].model if agents else "default-model")

        # Perform string replacements for placeholders
        persona = persona.replace("{task}", original_task)
        combination_instructions = combination_instructions.replace("{task}", original_task)

        super().__init__(task_description="", model=model, instructions=instructions, persona=persona)
        self.combination_instructions = combination_instructions

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
        moderator_task = self.combination_instructions.format(previous_responses=combined_responses_str)
        self.current_task_description = moderator_task
        return self.process_task(previous_responses=combined_responses_str)




class Chain:
    def __init__(self, agents: List[Agent], shuffle: bool = False, cycles: int = 1, last_n: int = 1,
                 moderated: Optional[bool] = None, moderator_config: Optional[Dict[str, Any]] = None):
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
        self.agents = agents
        self.shuffle = shuffle
        self.last_n = last_n
        self.cycles = cycles
        self.responses = []

        if shuffle:
            self.agents = random.sample(self.agents, len(self.agents))

        if moderator_config is not None:
            self.moderated = True
        else:
            self.moderated = False if moderated is None else moderated

        if self.moderated:
            self.moderator = Moderator(moderator_config=moderator_config, agents=agents)
        else:
            self.moderator = None

    def process_chain(self):
        """
        Process the task through a chain of agents, each building upon the last.
        """
        previous_responses = []
        original_task = self.agents[0].original_task_description if self.agents else "No task given"
        for _ in range(self.cycles):
            for agent in self.agents:
                previous_responses_slice = previous_responses[-self.last_n:]
                previous_responses_str = format_previous_responses(previous_responses_slice)
                response = agent.process_task(previous_responses_str)
                previous_responses.append(response)
                self.responses.append(response)

        if self.moderated and self.moderator:
            moderated_response = self.moderator.moderate_responses(self.responses, original_task)
            self.responses.append(moderated_response)
        self.final_response = self.responses[-1]
