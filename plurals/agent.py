from datetime import datetime
import pandas as pd
from typing import Optional, Dict, Any
from plurals.helpers import *
from litellm import completion


class Agent:
    """
    A class to represent an agent that processes tasks based on specific characteristics.

    Args:
        task_description (Optional[str]): The description of the task to be processed. This will be a user_prompt.
        data (Optional[pd.DataFrame]): The dataset used for generating persona descriptions if from dataset. But as of now, we only support ANES.
        persona_mapping (Optional[Dict[str, Any]]): Mapping to convert dataset rows into persona descriptions. As of now, we only support ANES.
        ideology (Optional[str]): Ideology can be `liberal` or `conservative` and if passed in, this will search ANES for rows where the participant is a liberal or conservative, and then condition the persona on that individual's other demographics.
        query_str (Optional[str]): A string used for a pandas query clause on the dataframe. As of now, we only support ANES.
        model (str): The model version to use for processing.
        system_instructions (Optional[str]): The complete system instructions. If this is included, it will override any persona and persona_template.
        persona_template (Optional[str]): Template for the persona description. This persona must have a ${persona} placeholder.
        persona (Optional[str]): The persona description to adopt for the task. This is a string that will be used with the `persona_template`.
        **kwargs: Additional keyword arguments.

    Attributes:
        task_description (Optional[str]): The description of the task to be processed. This will be a user_prompt.
        data (Optional[pd.DataFrame]): The dataset used for generating persona descriptions if from dataset. But as of now, we only support ANES.
        persona_mapping (Optional[Dict[str, Any]]): Mapping to convert dataset rows into persona descriptions. As of now, we only support ANES.
        ideology (Optional[str]): Ideology can be `liberal` or `conservative` and if passed in, this will search ANES for rows where the participant is a liberal or conservative, and then condition the persona on that individual's other demographics.
        query_str (Optional[str]): A string used for a pandas query clause on the dataframe. As of now, we only support ANES.
        model (str): The model version to use for processing.
        system_instructions (Optional[str]): The complete system instructions. If this is included, it will override any persona and persona_template.
        persona_template (Optional[str]): Template for the persona description. This persona must have a ${persona} placeholder.
        persona (Optional[str]): The persona description to adopt for the task. This is a string that will be used with the `persona_template`.
        **kwargs: Additional keyword arguments.
        original_task_description (str): The original task description without modifications.
        current_task_description (str): The current task description that appends `previous_responses'.
        data (pd.DataFrame): The dataset used for generating persona descriptions. As of now, we implement ANES.
        history (list): A list of dicts like {'prompt':prompt, 'response':response, 'model':model}

    Methods:
        process_task(previous_response=""): Process the task, optionally building upon a previous response.
        get_persona_description_ideology(data, ideology): Generates a persona description based on the dataset and ideology.
        filter_data_by_ideology(data, ideology): Filters the dataset based on the specified ideology.
        _get_response(task): Internal method to interact with the API and get a response.
        row2persona(row, persona_mapping): Converts a dataset row into a persona description string.
    """

    # noinspection PyTypeChecker
    def __init__(self,
                 task_description: Optional[str] = None,
                 data: Optional[pd.DataFrame] = None,
                 persona_mapping: Optional[Dict[str, Any]] = None,
                 ideology: Optional[str] = None,
                 query_str: Optional[str] = None,
                 model: str = "gpt-4o",
                 system_instructions: Optional[str] = None,
                 persona_template: Optional[str] = "default",
                 persona: Optional[str] = None,
                 **kwargs):
        self.model = model
        self.system_instructions = system_instructions
        self.history = []
        self.persona_mapping = persona_mapping
        self.task_description = task_description
        self.persona = persona
        self.ideology = ideology
        self.data = data if data is not None else self.load_default_data()
        self.query_str = query_str
        self.original_task_description = task_description
        self.current_task_description = task_description
        self.combination_instructions = None
        self.persona_template = persona_template
        self.defaults = load_yaml("instructions.yaml")
        self.validate()
        self.set_system_instructions()
        self.kwargs = kwargs

    def set_system_instructions(self):
        """
        Users can directly pass in system_instructions. Or, we can generate system instructions by combining a persona_template and a persona.
        """
        # If system_instructions is already provided, we don't need to do anything
        if self.system_instructions is not None:
            return

        # If system_instructions, persona, ideology, nor query_str is provided, set system_instructions to None
        if not self.system_instructions and not self.persona and not self.ideology and not self.query_str:
            self.system_instructions = None
            return

        # If persona is not already provided, generate it
        if not self.persona:
            self.persona = self._generate_persona()

        # Use the persona_template to create system_instructions
        self.persona_template = self.defaults['prefix_template'].get(self.persona_template, self.persona_template)
        self.system_instructions = SmartString(self.persona_template).format(persona=self.persona, task=self.task_description)

    def load_default_data(self) -> pd.DataFrame:
        """
        Load the default ANES dataset.

        Returns:
            pd.DataFrame: The loaded ANES dataset.
        """
        default_data_path = os.path.join(os.path.dirname(__file__), 'data', 'anes_pilot_2022_csv_20221214.csv')
        self.persona_mapping = load_yaml("anes-mapping.yaml")

        return pd.read_csv(default_data_path, low_memory=False)

    def _generate_persona(self) -> str:
        """
        Generates a persona based on the provided data, ideology, or query string.

        Returns:
            str: Generated persona description.
        """
        if self.ideology:
            return self.get_persona_description_ideology(self.data, self.ideology)
        elif self.query_str:
            return self.row2persona(self.data.query(self.query_str).sample(1).iloc[0], self.persona_mapping)
        return "No persona data available."

    def process_task(self, previous_responses: str = "") -> Optional[str]:
        """
        Process the task, optionally building upon a previous response.

        Args:
            previous_responses (str): The previous response to incorporate.

        Returns:
            Optional[str]: The response from the LLM.
        """
        if previous_responses:
            combined_responses = SmartString(self.combination_instructions).format(previous_responses=previous_responses)
            self.current_task_description = SmartString(f"{self.original_task_description}\n{combined_responses}")
        else:
            self.current_task_description = self.original_task_description
        return self._get_response(self.current_task_description)


    def get_persona_description_ideology(self, data: pd.DataFrame, ideology: str) -> str:
        """
        Generates a persona description based on the dataset and ideology.

        Args:
            data (pd.DataFrame): The dataset to use for generating persona descriptions.
            ideology (str): The ideological filter to apply.

        Returns:
            str: Generated persona description.
        """
        filtered_data = self.filter_data_by_ideology(data, ideology)
        if not filtered_data.empty:
            selected_row = filtered_data.sample(n=1).iloc[0]
            return self.row2persona(selected_row, self.persona_mapping)
        return "No data available for the specified ideology."

    def filter_data_by_ideology(self, data: pd.DataFrame, ideology: str) -> pd.DataFrame:
        """
        Filters the dataset based on the specified ideology.

        Args:
            data (pd.DataFrame): The dataset to filter.
            ideology (str): The ideological filter to apply.

        Returns:
            pd.DataFrame: Filtered dataset.
        """
        if ideology == 'liberal':
            return data[data['ideo5'].isin([1, 2])]
        elif ideology == 'conservative':
            return data[data['ideo5'].isin([4, 5])]
        return data

    def _get_response(self, task: str) -> Optional[str]:
        """
        Internal method to interact with the LLM API and get a response.

        Args:
            task (str): The task description to send to the LLM.

        Returns:
            Optional[str]: The response from the LLM.
        """
        if self.system_instructions:
            messages = [
                {"role": "system", "content": self.system_instructions},
                {"role": "user", "content": task}
            ]
        else:
            messages = [
                {"role": "user", "content": task}
            ]
        try:
            response = completion(model=self.model, messages=messages, **self.kwargs)
            content = response.choices[0].message.content
            self.history.append({'prompts': messages, 'response': content, 'model': self.model})
            return content
        except Exception as e:
            print(f"Error fetching response from LLM: {e}")
            return None

    @staticmethod
    def row2persona(row: pd.Series, persona_mapping: Dict[str, Any]) -> str:
        """
        Converts a dataset row into a persona description string.

        Args:
            row (pd.Series): The dataset row to convert.
            persona_mapping (Dict[str, Any]): Mapping to convert dataset rows into persona descriptions.

        Returns:
            str: Generated persona description.
        """
        persona_description_str = ""
        for key, value in persona_mapping.items():
            field_name = value['name']
            if key == 'race':
                race_found = False
                for race_key in ['eth', 'rwh', 'rbl', 'rain', 'ras', 'rpi', 'roth']:
                    if race_key in row and str(row[race_key]) == '1':
                        race_description = value['values'][race_key].get('1', 'Unknown')
                        if race_description:
                            persona_description_str += f"{field_name} {race_description}. "
                            race_found = True
                            break
                if not race_found:
                    persona_description_str += f"{field_name} Unknown. "
            elif key in row:
                if key == "birthyr_dropdown" and 'integer' in value['values']:
                    age = datetime.now().year - row[key]
                    persona_description_str += f"{field_name} {age}. "
                else:
                    mapped_value = value['values'].get(str(row[key]), 'Unknown')
                    if "inapplicable" not in mapped_value.lower() and "legitimate skip" not in mapped_value.lower() and "unknown" not in mapped_value.lower():
                        persona_description_str += f"{field_name} {mapped_value}. "
        return persona_description_str.lower()

    def validate(self):
        """
        Validates the necessary attributes for the Agent.
        """
        #  assert self.original_task_description is not None, "Need to provide some task instructions"
        if self.ideology or self.query_str:
            assert self.data is not None and self.persona_mapping is not None, "If you use either `ideology` or `query_str` you need to provide both a dataframe and a persona mapping to process rows of the dataframe."

        # cannot pass in system_instructions AND (persona_template or persona)
        if self.system_instructions:
            assert not (
                    self.persona_template != 'default' or self.persona), "Cannot pass in system_instructions AND (persona_template or persona)"
