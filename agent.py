# plurals/agent.py

import random
from datetime import datetime
import openai  # Assuming you're using OpenAI's API for the LLM
import pandas as pd
from typing import Optional, Dict, Any
import yaml
import os
from plurals.helpers import *
from litellm import completion


class Agent:
    """
    A class to represent an agent that processes tasks based on specific characteristics.

    Attributes:
        model (str): The model version to use for processing.
        task_description (str): The description of the task to be processed.
        persona (str): The persona description to adopt for the task.
        system_instructions (str): The complete system instructions including persona and constraints.
        original_task_description (str): The original task description without modifications.
        current_task_description (str): The current task description that may include modifications.
        data (pd.DataFrame): The dataset used for generating persona descriptions.
        persona_mapping (dict): Mapping to convert dataset rows into persona descriptions.
        ideology (str): The ideological filter to apply when selecting data for persona generation.
        query_str (str): A string used for a pandas query clause on the dataframe.
        history (list): A list of dicts like {'prompt':prompt, 'response':response, 'model':model}
    Methods:
        process_task(previous_response=""): Process the task, optionally building upon a previous response.
        get_persona_description_ideology(data, ideology): Generates a persona description based on the dataset and ideology.
        filter_data_by_ideology(data, ideology): Filters the dataset based on the specified ideology.
        _get_response(task): Internal method to interact with the API and get a response.
        row2persona(row, persona_mapping): Converts a dataset row into a persona description string.
    """

    def __init__(self,
                 task_description: str,
                 data: Optional[pd.DataFrame] = None,
                 persona_mapping: Optional[Dict[str, Any]] = None,
                 ideology: Optional[str] = None,
                 query_str: Optional[str] = None,
                 model: str = "gpt-4-turbo-preview",
                 instructions: Optional[Dict[str, Any]] = None,
                 persona: str = "",
                 mode: Optional[str]= 'chain'):
        """
        Initialize an agent with specific characteristics and dataset.
        """
        self.model = model
        self.history = []
        self.persona_mapping = persona_mapping
        self.task_description = task_description
        self.persona = persona
        self.ideology = ideology
        self.data = data if data is not None else self.load_default_data()
        self.query_str = query_str
        self.original_task_description = task_description
        self.current_task_description = task_description
        self.instructions = instructions if instructions is not None else load_yaml("instructions.yaml")
        self.persona_template = self.instructions['prefix_template']
        
        #E.F.6/17
        self.mode = mode
        self.combination_instructions = self.instructions['combination_instructions_chain'] if mode == 'chain' else \
            self.instructions['combination_instructions_debate']             
        self.combination_instructions = self.instructions['combination_instructions']
       
        self.validate()
        if not self.persona:
            self.persona = self._generate_persona()

        self.system_instructions = self.persona_template.format(persona=self.persona)

    def load_default_data(self) -> pd.DataFrame:
        """
        Load the default ANES dataset.

        Returns:
            pd.DataFrame: The loaded ANES dataset.
        """
       # E.F.06/17  
        self.persona_mapping = load_yaml("anes-mapping.yaml")
        
        default_data_path = os.path.join(os.path.dirname(__file__), 'data', 'anes_pilot_2022_csv_20221214.csv')
        return pd.read_csv(default_data_path)

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
        task = self.original_task_description
        if previous_responses:
            task += f"\n{self.combination_instructions.format(previous_responses=previous_responses)}"
        self.current_task_description = task
        return self._get_response(task)

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
        messages = [
            {"role": "system", "content": self.system_instructions},
            {"role": "user", "content": task}
        ]
        try:
            # This is a placeholder function. Replace with actual API call.
            response = completion(model=self.model, messages=messages)

            content = response.choices[0].message.content
            self.history.append({'prompts':messages, 'response':content, 'model':self.model})
            return content

        except Exception as e:
            print(f"Error in _get_response: {e}")
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
        assert self.original_task_description is not None, "Need to provide some task instructions"
        if self.ideology or self.query_str:
            assert self.data is not None and self.persona_mapping is not None, "If you use either `ideology` or `query_str` you need to provide both a dataframe and a persona mapping to process rows of the dataframe."
