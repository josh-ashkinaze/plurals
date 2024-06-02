# plurals/deliberation.py

from typing import List, Optional, Dict, Any
import random
from .agent import Agent
from .helpers import load_yaml, format_previous_responses

class Moderator:
    def __init__(self, moderator_config: Optional[Dict[str, Any]] = None,
                 instructions_file: str = "instructions.yaml",
                 model: str = "gpt-4-turbo-preview"):
        """
        Initialize the moderator with specific characteristics.
        """
        if moderator_config is not None:
            self.moderator_config = moderator_config
        else:
            instructions = load_yaml(instructions_file)
            self.moderator_config = {
                'moderator_persona': instructions['moderator_persona'],
                'moderator_instructions': instructions['moderator_instructions']
            }
        self.moderator_persona = self.moderator_config['moderator_persona']
        self.moderator_instructions = self.moderator_config['moderator_instructions']
        self.model = model

    def moderate_responses(self, responses: List[str], original_task: str) -> str:
        """
        Combine responses using the moderator persona and instructions.
        """
        combined_responses_str = format_previous_responses(responses)
        moderator_task = self.moderator_instructions.format(task=original_task, previous_responses=combined_responses_str)
        moderator_agent = Agent(
            task_description=moderator_task,
            persona=self.moderator_persona,
            model=self.model  # Inherit the model from agents
        )
        return moderator_agent.process_task()


class Chain:
    def __init__(self, agents: List[Agent], shuffle: bool = False, cycles: int = 1, last_n: int = 1,
                 moderated: bool = False, moderator_config: Optional[Dict[str, Any]] = None,
                 instructions_file: str = "instructions.yaml"):
        """
        Initialize a chain with a list of agents.
        """
        self.agents = agents
        self.responses = []
        self.prompts = []
        self.final_response = None
        self.shuffle = shuffle
        self.last_n = last_n
        self.moderated = moderated
        self.cycles = cycles

        if self.shuffle:
            self.agents = random.sample(self.agents, len(self.agents))

        if self.moderated:
            model = agents[0].model if agents else "gpt-4-turbo-preview"
            self.moderator = Moderator(moderator_config=moderator_config, instructions_file=instructions_file, model=model)

    def process_chain(self):
        """
        Process the task through a chain of agents, each building upon the last.
        """
        previous_responses = []
        original_task = self.agents[0].original_task_description if self.agents else ""
        for _ in range(self.cycles):
            for agent in self.agents:
                previous_responses_slice = previous_responses[-self.last_n:]
                previous_responses_str = format_previous_responses(previous_responses_slice)
                response = agent.process_task(previous_responses_str)
                previous_responses.append(response)
                self.prompts.append(agent.current_task_description)
                self.responses.append(response)

        if self.moderated:
            self.final_response = self.moderator.moderate_responses(self.responses, original_task)
        else:
            self.final_response = self.responses[-1]


