import warnings
import os
from typing import Optional, Dict, Any

import pandas as pd
from litellm import completion

from plurals.helpers import *

from pprint import pformat

DEFAULTS = load_yaml("instructions.yaml")
DEFAULTS = strip_nested_dict(DEFAULTS)


def _load_global_anes_data():
    """
    Load global ANES data for the agent. As per codebook page 2 section 1, the cases that don't have weights are
    not meant for population inference.

    Here is the codebook url:
    https://electionstudies.org/wp-content/uploads/2024/03/anes_pilot_2024_userguidecodebook_20240319.pdf

    Loads:
    - PERSONA_MAPPING: Mapping for converting dataset rows to persona descriptions.
    - DATASET: ANES dataset for persona and ideological queries
    """
    global PERSONA_MAPPING, DATASET
    PERSONA_MAPPING = load_yaml("anes-mapping.yaml")
    DATASET = pd.read_csv(
        os.path.join(
            os.path.dirname(__file__),
            'data',
            'anes_pilot_2024_20240319.csv'),
        low_memory=False)
    DATASET.dropna(subset=['weight'], inplace=True)
    DATASET['age'] = 2024 - DATASET['birthyr']


_load_global_anes_data()

from abc import ABC, abstractmethod


# Strategy Interfaces and Implementations

class SystemInstructionStrategy(ABC):
    @abstractmethod
    def set_system_instructions(self, agent):
        pass


class DirectSystemInstructionStrategy(SystemInstructionStrategy):
    def set_system_instructions(self, agent):
        # System instructions are already provided directly; nothing to do.
        pass


class DefaultSystemInstructionStrategy(SystemInstructionStrategy):
    def set_system_instructions(self, agent):
        # No system instructions, personas, or ideologies are provided.
        agent.system_instructions = None


class PersonaBasedSystemInstructionStrategy(SystemInstructionStrategy):
    def set_system_instructions(self, agent):
        # Use the persona strategy to generate the persona
        agent.persona = agent.persona_strategy.generate_persona(agent)

        # Use the persona_template to create system_instructions
        agent.persona_template = agent.defaults['persona_template'].get(
            agent.persona_template, agent.persona_template).strip()
        agent.system_instructions = SmartString(
            agent.persona_template).format(
            persona=agent.persona,
            task=agent.task_description).strip()


class PersonaStrategy(ABC):
    @abstractmethod
    def generate_persona(self, agent):
        pass


class DirectPersonaStrategy(PersonaStrategy):
    def generate_persona(self, agent):
        # Persona is directly provided by the user
        return agent.persona


class RandomPersonaStrategy(PersonaStrategy):
    def generate_persona(self, agent):
        # Generate a random persona from the data
        selected_row = agent.data.sample(n=1, weights=agent.data['weight']).iloc[0]
        return agent.persona_generator.row_to_persona(selected_row, agent.persona_mapping)


class IdeologyPersonaStrategy(PersonaStrategy):
    def generate_persona(self, agent):
        # Filter data based on ideology and generate persona
        filtered_data = agent.data_filter_strategy.filter_data(agent)
        if filtered_data.empty:
            raise AssertionError("No data found satisfying conditions")
        selected_row = filtered_data.sample(n=1, weights=filtered_data['weight']).iloc[0]
        return agent.persona_generator.row_to_persona(selected_row, agent.persona_mapping)


class QueryPersonaStrategy(PersonaStrategy):
    def generate_persona(self, agent):
        # Filter data based on query string and generate persona
        filtered_data = agent.data_filter_strategy.filter_data(agent)
        if filtered_data.empty:
            raise AssertionError("No data found satisfying conditions")
        selected_row = filtered_data.sample(n=1, weights=filtered_data['weight']).iloc[0]
        return agent.persona_generator.row_to_persona(selected_row, agent.persona_mapping)


class PersonaGenerator:
    @staticmethod
    def row_to_persona(row: pd.Series, persona_mapping: Dict[str, Any]) -> str:
        """
        Converts a dataset row into a persona description string.

        Args:
            row (pd.Series): The dataset row to convert.
            persona_mapping (Dict[str, Any]): Mapping to convert dataset rows into persona descriptions.

        Returns:
            str: Generated persona description.
        """
        persona = []
        for var, details in persona_mapping.items():
            value = row.get(var)

            if var == "age" and value is not None:
                value = int(value)

            if value is None or pd.isna(value) or (details.get('bad_vals') and str(value) in details['bad_vals']):
                continue

            if details.get('recode_vals') and str(value) in details['recode_vals']:
                value = details['recode_vals'][str(value)]

            clean_name = details['name']
            persona.append(f"{clean_name} {str(value).lower()}.")
        return " ".join(persona)


class DataFilterStrategy(ABC):
    @abstractmethod
    def filter_data(self, agent) -> pd.DataFrame:
        pass


class IdeologyDataFilterStrategy(DataFilterStrategy):
    def filter_data(self, agent) -> pd.DataFrame:
        try:
            ideology = agent.ideology.lower()
            if ideology == 'liberal':
                return agent.data[agent.data['ideo5'].isin(['Liberal', 'Very liberal'])]
            elif ideology == 'conservative':
                return agent.data[agent.data['ideo5'].isin(['Conservative', 'Very conservative'])]
            elif ideology == 'moderate':
                return agent.data[agent.data['ideo5'] == 'Moderate']
            elif ideology == 'very liberal':
                return agent.data[agent.data['ideo5'] == 'Very liberal']
            elif ideology == 'very conservative':
                return agent.data[agent.data['ideo5'] == 'Very conservative']
            else:
                return pd.DataFrame()
        except Exception as e:
            raise AssertionError(f"Error filtering data by ideology: {e}")


class QueryDataFilterStrategy(DataFilterStrategy):
    def filter_data(self, agent) -> pd.DataFrame:
        try:
            return agent.data.query(agent.query_str)
        except Exception as e:
            raise AssertionError(f"Error filtering data by query string: {e}")


# Agent Class

class Agent:
    """
    Agents are LLMs with customizable personas, who complete tasks with other Agents working together in Structures.
    Personas of Agents can be instantiated directly, null (i.e., default system prompt), or leverage external datasets
    like ANES for nationally-representative personas.

    The main attributes of the Agent class are:

    1. ``system_instructions``: Set either directly or through various persona methods.

    2. ``combination_instructions``: Dictates how Agents should combine previous responses with the current task.

    3. ``task``: The task (i.e., user prompt) that Agents respond to.

    Agents can be used alone or in conjunction with Structures to create multi-agent simulations.

    Args:
        task (Optional[str]): Description of the task for the agent to process. If the agent is part of a structure,
            and the task is provided to the structure, then the agent will inherit that task.
        combination_instructions (Optional[str]): Instructions for combining previous responses with the current
            task. If the agent is part of a structure and the combination_instructions are provided to the structure,
            then the agent will inherit those combination instructions. Must include a ${previous_responses}
            placeholder.
        ideology (Optional[str]): Ideological perspective to influence persona creation, supported values are
                                  ['liberal', 'conservative', 'moderate', 'very liberal', 'very conservative'].
        query_str (Optional[str]): Custom query string for filtering the ANES dataset according to specific criteria.
        model (str): The language model version to use for generating responses.
        system_instructions (Optional[str]): Overrides automated instructions with a custom set of directives for the
            model.
        persona_template (Optional[str]): Template string for constructing the persona. If passing your own, you must include a ${persona}
            placeholder. You can pass in the names of templates located in `instructions.yaml` [1]. If not supplied: When using an ANES-generated persona the `anes` template will be used.
            Otherwise, the `default` template will be used. Current templates: https://github.com/josh-ashkinaze/plurals/blob/main/plurals/instructions.yaml
        persona (Optional[str]): Direct specification of a persona description.
        kwargs (Optional[dict]): Additional keyword arguments for the model's completion function. These are provided by LiteLLM. Enter `help(litellm.completion)` for details. LiteLLM completion function: https://litellm.vercel.app/docs/completion/input#input-params-1

    Attributes:
        persona_mapping (Optional[Dict[str, Any]]): Dictionary to map dataset rows to persona descriptions.
        data (pd.DataFrame): Loaded dataset for persona and ideological queries.
        system_instructions (Optional[str]): Final system instructions for the agent to follow. The system
            instructions can be set directly or generated from a persona-based method.
        original_task_description (str): The original, unmodified task description.
        current_task_description (str): Dynamically updated task description that may include prior responses.
        history (list): Chronological record of prompts, responses, and models used during the agent's operation.
        responses (list): List of responses generated by the agent (the same information can be accessed by history)
        prompts (list): List of prompts that generated the responses (the same information can be accessed by history)
        info (dict): Comprehensive attributes of the agent's current configuration and state.

    Notes:
        Note that when used with Structures, the agent-level attribute values will override. Eg: If you set a task
        at an agent level and a Structure-level, the agent-level task will be used.
    """

    def __init__(self,
                 task: Optional[str] = None,
                 combination_instructions: Optional[str] = None,
                 ideology: Optional[str] = None,
                 query_str: Optional[str] = None,
                 model: str = "gpt-4o",
                 system_instructions: Optional[str] = None,
                 persona_template: Optional[str] = None,
                 persona: Optional[str] = None,
                 kwargs: Optional[Dict[str, Any]] = None):
        self.model = model
        self.system_instructions = system_instructions
        self.combination_instructions = combination_instructions
        self._history = []
        self.persona_mapping = PERSONA_MAPPING
        self.data = DATASET
        self.task_description = task
        self.persona = persona
        self.ideology = ideology
        self.query_str = query_str
        self.original_task_description = task
        self.current_task_description = task
        self.defaults = DEFAULTS
        self.persona_template = self.handle_default_persona_template() if not persona_template else persona_template
        self.kwargs = kwargs if kwargs is not None else {}

        # Initialize strategies
        self.persona_generator = PersonaGenerator()
        self.persona_strategy = self._get_persona_strategy()
        self.data_filter_strategy = self._get_data_filter_strategy()
        self.system_instruction_strategy = self._get_system_instruction_strategy()

        # Validate inputs
        self._validate_templates()
        self._validate_system_instructions()

        # Use strategy to set system instructions
        self._set_system_instructions()

    def _get_persona_strategy(self):
        if self.persona and self.persona != "random":
            return DirectPersonaStrategy()
        elif self.persona == "random":
            return RandomPersonaStrategy()
        elif self.ideology:
            return IdeologyPersonaStrategy()
        elif self.query_str:
            return QueryPersonaStrategy()
        else:
            return None

    def _get_data_filter_strategy(self):
        if self.ideology:
            return IdeologyDataFilterStrategy()
        elif self.query_str:
            return QueryDataFilterStrategy()
        else:
            return None

    def _get_system_instruction_strategy(self):
        if self.system_instructions is not None:
            return DirectSystemInstructionStrategy()
        elif not self.system_instructions and not self.persona and not self.ideology and not self.query_str:
            self.system_instructions = None
            return DefaultSystemInstructionStrategy()
        else:
            return PersonaBasedSystemInstructionStrategy()

    def _set_system_instructions(self):
        self.system_instruction_strategy.set_system_instructions(self)

    def process(
            self,
            task: Optional[str] = None,
            previous_responses: str = "",
    ) -> Optional[str]:
        """
        Process the task, optionally building upon a previous response. If you pass in a task, it will replace the
        Agent's initialized task description. If you pass in a previous responses, it will be incorporated into the task
        description if ``combination_instructions`` have not been set.

        Args:
            previous_responses (str): The previous responses to incorporate.
            task (Optional[str]): The task description to process. If not provided, the agent will use its current task.

        Returns:
            Optional[str]: The response from the LLM.
        """
        if task:
            self.set_task(task)

        if previous_responses:
            # Update the task description with the previous responses
            combined_responses = SmartString(
                self.combination_instructions).format(
                previous_responses=previous_responses)
            if self.current_task_description:
                self.current_task_description = SmartString(
                    f"{self.current_task_description}\n{combined_responses}")
            else:
                self.current_task_description = SmartString(
                    f"{self.original_task_description}\n{combined_responses}")
            self.current_task_description = self.current_task_description.strip()
        else:
            self.current_task_description = self.original_task_description.strip()
        return self._get_response(self.current_task_description)

    def _get_response(self, task: str) -> Optional[str]:
        """
        Internal method to interact with the LLM API and get a response.

        Args:
            task (str): The task description to send to the LLM.

        Returns:
            Optional[str]: The response from the LLM.
        """
        if self.system_instructions:
            messages = [{"role": "system", "content": self.system_instructions}, {"role": "user", "content": task}]
        else:
            messages = [{"role": "user", "content": task}]
        try:
            response = completion(
                model=self.model,
                messages=messages,
                **self.kwargs)
            content = response.choices[0].message.content
            prompts = {
                'system': next((msg['content'] for msg in messages if msg['role'] == 'system'), None),
                'user': next((msg['content'] for msg in messages if msg['role'] == 'user'), None)}
            self._history.append(
                {'prompts': prompts, 'response': content, 'model': self.model})
            return content
        except Exception as e:
            print(f"Error fetching response from LLM: {e}")
            return None

    def _validate_system_instructions(self):
        """
        Validates the system instructions arguments.

        Errors raised if:
        - ideology or query_str is passed in without data and persona_mapping
        - system_instructions is passed in with persona or persona_template
        - ideology or query_str is passed in with persona
        - ideology is passed in and it's not in  ['liberal', 'conservative', 'moderate', 'very liberal',
        'very conservative']
        """
        if self.ideology or self.query_str:
            assert self.data is not None and self.persona_mapping is not None, ("If you use either `ideology` or "
                                                                                "`query_str` you need to provide both "
                                                                                "a dataframe and a persona mapping to "
                                                                                "process rows of the dataframe.")

        if (sum([bool(self.ideology), bool(self.query_str), bool(self.persona),
                 bool(self.system_instructions)]) > 1):
            raise AssertionError("You can only pass in one of ideology, query_str, system_instructions, or persona")

        if self.ideology:
            allowed_vals = [
                'liberal',
                'conservative',
                'moderate',
                'very liberal',
                'very conservative']
            assert self.ideology in allowed_vals, f"Ideology has to be one of: {str(allowed_vals)}"

    def _validate_templates(self):
        """
        Errors raised if:
        - a user passes in persona_template but it does not contain a persona placeholder (so there is no way to
        format it)
        """
        if self.persona_template:
            default_templates = list(self.defaults['persona_template'].keys())

            assert '${persona}' in self.persona_template or self.persona_template in default_templates, (
                    "If you pass in a custom persona_template, it must contain a ${persona} placeholder or be one of the default templates:" + str(
                default_templates))

    @property
    def history(self):
        """
        An Agent's history

        Returns:
            list: A list of dictionaries containing the prompts, responses, and models used during the agent's operation.
        """
        if not self._history:
            warnings.warn("Be aware: No Agent history was found since tasks have not been processed yet.")
            return None
        else:
            return self._history

    @property
    def _info(self):
        """
        This is a private property, mainly used for debugging and testing. It includes more than in the user-facing info.
        """
        return {
            "original_task": self.original_task_description,
            "current_task_description": self.current_task_description,
            "system_instructions": self.system_instructions,
            "history": self.history,
            "persona": self.persona,
            "ideology": self.ideology,
            "query_str": self.query_str,
            "model": self.model,
            "persona_template": self.persona_template,
            "combination_instructions": self.combination_instructions,
            "kwargs": self.kwargs}

    @property
    def info(self):
        """
        Info of Agent

        Returns:
            dict: Comprehensive attributes of the agent's current configuration and state
        """
        return {
            "original_task": self.original_task_description,
            "current_task_description": self.current_task_description,
            "system_instructions": self.system_instructions,
            "history": self.history,
            "persona": self.persona,
            "persona_template": self.persona_template if self.persona else None,
            "combination_instructions": self.combination_instructions,
            "model": self.model,
            "kwargs": self.kwargs}

    @property
    def responses(self):
        """
        The responses to prompts

        Returns:
            list: List of responses generated by the agent
        """
        history = self.history
        if not history:
            warnings.warn("Be aware: No Agent history was found since tasks have not been processed yet.")
            return None
        return [history[i]['response'] for i in range(len(history))]

    @property
    def prompts(self):
        """
        The prompts that generated the responses

        Returns:
            list: List of prompts that generated the responses.
        """
        history = self.history
        if not history:
            warnings.warn("Be aware: No Agent history was found since tasks have not been processed yet.")
            return None
        return [history[i]['prompts'] for i in range(len(history))]

    def __repr__(self):
        return pformat(self.info, indent=2)

    def set_task(self, task: str):
        """
        Set the task description for the agent to process.

        Args:
            task (str): The new task description.

        Returns:
            None

        Sets:
            self.original_task_description: The original, unmodified task description.
            self.current_task_description: Dynamically updated task description that may include prior responses
        """
        self.original_task_description = task
        self.current_task_description = task

    def is_anes_persona(self) -> bool:
        """
        Returns:
            bool: Whether the persona is an ANES-generated persona.
        """
        if self.ideology or self.query_str:
            return True
        if self.persona == "random":
            return True
        else:
            return False

    def handle_default_persona_template(self):
        """The default persona template should be `default' if not ANES persona else 'anes'"""
        if self.is_anes_persona():
            return "anes"
        else:
            return "default"
