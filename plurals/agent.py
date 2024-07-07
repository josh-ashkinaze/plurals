import warnings
from typing import Optional, Dict

import pandas as pd
from litellm import completion

from plurals.helpers import *

DEFAULTS = load_yaml("instructions.yaml")


class Agent:
    """
    A class to represent an agent that processes tasks based on specific characteristics.

    Args:
        task (Optional[str]): The description of the task to be processed. This will be a user_prompt.
        ideology (Optional[str]): Ideology can in  ['liberal', 'conservative', 'moderate', 'very liberal', 'very conservative'].  And if passed in, this will search ANES 2024 for rows where the participant is a liberal or conservative or moderate, and then condition the persona on that individual's other demographics.
        query_str (Optional[str]): A string used for a pandas query clause on the ANES 2024 data. 
        model (str): The model version to use for processing.
        system_instructions (Optional[str]): The complete system instructions. If this is included, it will override any persona and persona_template.
        persona_template (Optional[str]): Template for the persona description. This persona must have a ${persona} placeholder.
        persona (Optional[str]): The persona description to adopt for the task. This is a string that will be used with the `persona_template`.
        **kwargs: Additional keyword arguments. These are from LiteLLM's completion function. (see here: https://litellm.vercel.app/docs/completion/input)

    Attributes:
        task (Optional[str]): The description of the task to be processed. This will be a user_prompt.
        persona_mapping (Optional[Dict[str, Any]]): Mapping to convert dataset rows into persona descriptions. As of now, we only support ANES.
        ideology (Optional[str]): Ideology can be `liberal` or `conservative` and if passed in, this will search ANES for rows where the participant is a liberal or conservative, and then condition the persona on that individual's other demographics.
        query_str (Optional[str]): A string used for a pandas query clause on the dataframe. As of now, we only support ANES.
        model (str): The model version to use for processing.
        system_instructions (Optional[str]): The complete system instructions. If this is included, it will override any persona and persona_template.
        persona_template (Optional[str]): Template for the persona description. This persona must have a ${persona} placeholder.
        persona (Optional[str]): The persona description to adopt for the task. This is a string that will be used with the `persona_template`.
        **kwargs: Additional keyword arguments. These are from LiteLLM's completion function. (see here: https://litellm.vercel.app/docs/completion/input)
        system_instructions (Optional[str]): The complete system instructions.
        original_task_description (str): The original task description without modifications.
        current_task_description (str): The current task description that appends `previous_responses'.
        history (list): A list of dicts like {'prompt':prompt, 'response':response, 'model':model}
        info (dict): A dictionary of different attributes of the agent. Contains keys for: 'task', 'system_instructions', 'history', 'persona', 'ideology', 'query_str', 'model', 'persona_template', and 'kwargs'
    """

    def __init__(self, task: Optional[str] = None, data: Optional[pd.DataFrame] = None,
                 persona_mapping: Optional[Dict[str, Any]] = None, ideology: Optional[str] = None,
                 query_str: Optional[str] = None, model: str = "gpt-4o", system_instructions: Optional[str] = None,
                 persona_template: Optional[str] = "default", persona: Optional[str] = None, **kwargs):
        self.model = model
        self.system_instructions = system_instructions
        self._history = []
        self.persona_mapping = persona_mapping
        self.task_description = task
        self.persona = persona
        self.ideology = ideology
        self.data = data if data is not None else self._load_default_data()
        self.query_str = query_str
        self.original_task_description = task
        self.current_task_description = task
        self.combination_instructions = None
        self.defaults = DEFAULTS
        self.persona_template = persona_template
        self._validate_templates()
        self._validate_system_instructions()
        self._set_system_instructions()
        self.kwargs = kwargs

    def _set_system_instructions(self):
        """
        Users can directly pass in system_instructions. Or, we can generate system instructions by combining a persona_template and a persona.

        In these two cases, persona_template does not do anything since system_instructions is set directly or is None.
        - If system_instructions is already provided, we don't need to do anything since system_instructions is already set.
        - If neither system_instructions, persona, ideology, nor query_str is provided (default) set system_instructions to None.

        Otherwise, we generate system instructions using a persona:
        - If persona is directly provided, use this.
        - If persona is "random" generate a random ANES persona
        - If persona is not already provided, generate it. This can be generated from a `query_str` or from `ideology`.
        """
        # If system_instructions is already provided, we don't need to do anything
        if self.system_instructions is not None:
            return

        # If system_instructions, persona, ideology, nor query_str is provided, set system_instructions to None
        if not self.system_instructions and not self.persona and not self.ideology and not self.query_str:
            self.system_instructions = None
            return

        # If persona is already provided, use it.
        if self.persona:
            self.persona = self.persona

        # If persona is "random" generate a random ANES persona
        if self.persona == "random":
            self.persona = self._generate_persona()

        # If persona is not already provided, generate it
        if not self.persona:
            self.persona = self._generate_persona()

        # Use the persona_template to create system_instructions
        self.persona_template = self.defaults['persona_template'].get(self.persona_template,
                                                                      self.persona_template).strip()
        self.system_instructions = SmartString(self.persona_template).format(persona=self.persona,
                                                                             task=self.task_description).strip()

    def _load_default_data(self) -> pd.DataFrame:
        """
        Load the default ANES dataset.

        Returns:
            pd.DataFrame: The loaded ANES dataset.
        """
        default_data_path = os.path.join(os.path.dirname(__file__), 'data', 'anes_pilot_2024_20240319.csv')
        self.persona_mapping = load_yaml("anes-mapping.yaml")
        dataset = pd.read_csv(default_data_path, low_memory=False)

        # As per codebook page 2 section 1, 409 cases don't have weights and are not meant
        # for population inference.
        # codebook url:
        # https://electionstudies.org/wp-content/uploads/2024/03/anes_pilot_2024_userguidecodebook_20240319.pdf
        dataset = dataset.dropna(subset=['weight'])
        return dataset

    # noinspection PyTypeChecker
    def _generate_persona(self) -> str:
        """
        Generates a persona based on the provided data, ideology, or query string.

        Returns:
            str: Generated persona description.
        """
        if self.persona == "random":
            return self._get_random_persona(self.data)
        if self.ideology:
            self.query_str = self._convert_ideology_to_query_str(self.ideology)
            filtered_data = self.data.query(self.query_str)
            if filtered_data.empty: raise AssertionError("No data found satisfying conditions")
            selected_row = filtered_data.sample(n=1, weights=filtered_data['weight']).iloc[0]
            return self._row2persona(selected_row, self.persona_mapping)
        elif self.query_str:
            filtered_data = self.data.query(self.query_str)
            if filtered_data.empty: raise AssertionError("No data found satisfying conditions")
            selected_row = filtered_data.sample(n=1, weights=filtered_data['weight']).iloc[0]
            return self._row2persona(selected_row, self.persona_mapping)

    def process(self, previous_responses: str = "") -> Optional[str]:
        """
        Process the task, optionally building upon a previous response.

        Args:
            previous_responses (str): The previous response to incorporate.

        Returns:
            Optional[str]: The response from the LLM.
        """
        if previous_responses:
            combined_responses = SmartString(self.combination_instructions).format(
                previous_responses=previous_responses)
            self.current_task_description = SmartString(f"{self.original_task_description}\n{combined_responses}")
        else:
            self.current_task_description = self.original_task_description
        return self._get_response(self.current_task_description)

    def _get_random_persona(self, data: pd.DataFrame) -> str:
        """
        Generates a random persona description based on the dataset.

        Args:
            data (pd.DataFrame): The dataset to use for generating persona descriptions.

        Returns:
            str: Generated persona description.
        """
        selected_row = data.sample(n=1, weights=data['weight']).iloc[0]
        return self._row2persona(selected_row, self.persona_mapping)

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
            response = completion(model=self.model, messages=messages, **self.kwargs)
            content = response.choices[0].message.content
            prompts = {'system': next((msg['content'] for msg in messages if msg['role'] == 'system'), None),
                       'user': next((msg['content'] for msg in messages if msg['role'] == 'user'), None)}
            self._history.append({'prompts': prompts, 'response': content, 'model': self.model})
            return content
        except Exception as e:
            print(f"Error fetching response from LLM: {e}")
            return None

    @staticmethod
    def _row2persona(row: pd.Series, persona_mapping: Dict[str, Any]) -> str:
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

            if var == "birthyr" and value is not None:
                value = 2024 - int(value)

            if value is None or (details.get('bad_vals') and str(value) in details['bad_vals']):
                continue

            if details.get('recode_vals') and str(value) in details['recode_vals']:
                value = details['recode_vals'][str(value)]

            clean_name = details['name']
            persona.append(f"{clean_name} {str(value).lower()}.")
        return " ".join(persona)

    def _validate_system_instructions(self):
        """
        Validates the system instructions arguments.

        Errors raised if:
        - ideology or query_str is passed in without data and persona_mapping
        - system_instructions is passed in with persona or persona_template
        - ideology or query_str is passed in with persona
        - ideology is passed in and it's not in  ['liberal', 'conservative', 'moderate', 'very liberal', 'very conservative']
        """
        #  assert self.original_task_description is not None, "Need to provide some task instructions"
        if self.ideology or self.query_str:
            assert self.data is not None and self.persona_mapping is not None, "If you use either `ideology` or `query_str` you need to provide both a dataframe and a persona mapping to process rows of the dataframe."

        # cannot pass in system_instructions AND (persona_template or persona)
        if self.system_instructions:
            assert not (
                    self.persona_template != 'default' or self.persona), "Cannot pass in system_instructions AND (persona_template or persona)"

        # cannot pass in (ideology or query_str) AND (persona)
        if self.ideology or self.query_str:
            assert not self.persona, "Cannot pass in (ideology or query_str) AND persona"

        # ideology must be in  ['liberal', 'conservative', 'moderate', 'very liberal', 'very conservative']
        if self.ideology:
            allowed_vals = ['liberal', 'conservative', 'moderate', 'very liberal', 'very conservative']
            assert self.ideology in allowed_vals, f"Ideology has to be one of: {str(allowed_vals)}"

    def _validate_templates(self):
        """
        Errors raised if:
        - a user passes in persona_template but it does not contain a persona placeholder (so there is no way to format it)
        """
        # if pass in persona_template, must contain persona placeholder
        if self.persona_template:
            default_templates = list(self.defaults['persona_template'].keys())

            assert '${persona}' in self.persona_template or self.persona_template in default_templates, "If you pass in a persona_template, it must contain a ${persona} placeholder or be one of the default templates:" + str(
                default_templates)

    def _convert_ideology_to_query_str(self, ideology: str) -> str:
        """
        Converts ideology to a query string for pandas DataFrame.
        """
        if ideology.lower() == 'liberal':
            return "ideo5=='Liberal'|ideo5=='Very liberal'"
        elif ideology.lower() == 'conservative':
            return "ideo5=='Conservative'|ideo5=='Very conservative'"
        elif ideology.lower() == 'moderate':
            return "ideo5 == 'Moderate'"
        elif ideology.lower() == "very liberal":
            return "ideo5 == 'Very liberal'"
        elif ideology.lower() == "very conservative":
            return "ideo5 == 'Very conservative'"
        return ""

    @property
    def history(self):
        if not self._history:
            warnings.warn("No history found. Please process a task first!")
            return None
        else:
            return self._history

    @property
    def info(self):
        return {"task": self.task_description, "system_instructions": self.system_instructions, "history": self.history,
                "persona": self.persona, "ideology": self.ideology, "query_str": self.query_str, "model": self.model,
                "persona_template": self.persona_template, "kwargs": self.kwargs}

    def __repr__(self):
        return str(self.info)
