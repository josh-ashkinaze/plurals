import warnings
from typing import Optional, Dict

import pandas as pd
from litellm import completion

from plurals.helpers import *

DEFAULTS = load_yaml("instructions.yaml")


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
    DATASET = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'anes_pilot_2024_20240319.csv'),
                          low_memory=False)
    DATASET.dropna(subset=['weight'], inplace=True)


_load_global_anes_data()


class Agent:
    """
    Represents an intelligent agent that processes tasks with customizable personas and ideological perspectives.
    This agent uses external data, like ANES 2024, to tailor responses based on demographic information associated
    with various ideologies. It can operate under specific system instructions or dynamically generate instructions
    using predefined templates.

    The agent interacts with language models to generate task-specific responses, potentially incorporating
    previous interactions to simulate a continuous dialogue or decision-making process.

    **Examples:**

        **Using Agent without a structure**: This allows you to see an agents response without using a structure.

        .. code-block:: python

            a = agent(task=“hello”)
            ans = a.process()

            pirate_agent = Agent(system_instructions="You are a pirate.", model='gpt-4o', task=task)
            response=pirate_agent.process()

        **Here is how to inspect the exact prompts an Agent is doing**:

        .. code-block:: python

            from plurals.agent import Agent
            a = Agent(ideology="very conservative", model='gpt-4o', task="A task here")
            a.process()
            print(a.info)
            print(a.history)
            print(a.responses)

        **Manual system instructions**: This allows you to set system instructions to whatever you would like.

        .. code-block:: python

            agent = Agent(system_instructions="You are a predictable independent", model='gpt-4o',
                          kwargs={'temperature': 0.1, 'max_tokens': 200})

        **No system instructions**: When no system instructions are inputted, agents will use default system instructions.

        .. code-block:: python

            agent = Agent(model='gpt-4o', kwargs={'temperature': 1, 'max_tokens': 500})

        **Persona Template**: Here, the user provides a persona_template and a persona (indicated by ${persona}).
        Or, the user can just use our default persona_template.

        .. code-block:: python

            agent = Agent(persona="a liberal", persona_template="default", model='gpt-4o')
            agent = Agent(persona="a moderate",
                          persona_template="When drafting feedback, adopt the following persona: ${persona}",
                          model='gpt-4o')

        **Ideology Matching**: We support an ideology keyword that can be one of
        ['very liberal', 'liberal', 'moderate', 'conservative', 'very conservative'] where the 'veries' are a
        subset of the normals.

        .. code-block:: python

            agent = Agent(ideology="very conservative", model='gpt-4o', task=task, persona_template='empathetic')

        **Random Sampling from ANES dataset**: If you make persona=='random' then we will randomly sample a row
        from ANES and use that as the persona.

        .. code-block:: python

            agent = Agent(persona='random', model='gpt-4o', task=task)

        **Pandas Query String**: If you want to get more specific, you can pass in a query string that will be used to filter
        the ANES dataset.

        .. code-block:: python

            agent = Agent(query_str="inputstate=='West Virginia' & ideo5=='Very conservative'", model='gpt-4o', task=task)
    Args:
        task (Optional[str]): Description of the task for the agent to process. If the agent is part of a structure,
            and the task is provided to the structure, then the agent will inherit that task.
        combination_instructions (Optional[str]): Instructions for combining previous responses with the current
            task. If the agent is part of a structure and the combination_instructions are provided to the structure,
            then
            the agent will inherit those combination instructions.
        ideology (Optional[str]): Ideological perspective to influence persona creation, supported values are
                                  ['liberal', 'conservative', 'moderate', 'very liberal', 'very conservative'].
        query_str (Optional[str]): Custom query string for filtering the ANES dataset according to specific criteria.
        model (str): The language model version to use for generating responses.
        system_instructions (Optional[str]): Overrides automated instructions with a custom set of directives for the
            model.
        persona_template (Optional[str]): Template string for constructing the persona, must include a ${persona}
            placeholder.
        persona (Optional[str]): Direct specification of a persona description.
        **kwargs: Additional keyword arguments for the model's completion function. These are provided by LiteLLM (
            https://litellm.vercel.app/docs/completion/input#input-params-1). Enter `help(litellm.completion)` for
            details.

    Attributes:
        persona_mapping (Optional[Dict[str, Any]]): Dictionary to map dataset rows to persona descriptions.
        data (pd.DataFrame): Loaded dataset for persona and ideological queries.
        system_instructions (Optional[str]): Final system instructions for the agent to follow. The system
            instructions can be set directly or generated from a persona-based method.
        original_task_description (str): The original, unmodified task description.
        current_task_description (str): Dynamically updated task description that may include prior responses.
        history (list): Chronological record of prompts, responses, and models used during the agent's operation.
        info (dict): Comprehensive attributes of the agent's current configuration and state.
    """

    def __init__(self,
                 task: Optional[str] = None,
                 combination_instructions: Optional[str] = None,
                 ideology: Optional[str] = None,
                 query_str: Optional[str] = None,
                 model: str = "gpt-4o",
                 system_instructions: Optional[str] = None,
                 persona_template: Optional[str] = "default",
                 persona: Optional[str] = None,
                 **kwargs):
        self.model = model
        self.system_instructions = system_instructions
        self.combination_instructions = combination_instructions
        self._history = []
        self.persona_mapping = PERSONA_MAPPING
        self.task_description = task
        self.persona = persona
        self.ideology = ideology
        self.data = DATASET
        self.query_str = query_str
        self.original_task_description = task
        self.current_task_description = task
        self.defaults = DEFAULTS
        self.persona_template = persona_template
        self._validate_templates()
        self._validate_system_instructions()
        self._set_system_instructions()
        self.kwargs = kwargs

    def _set_system_instructions(self):
        """
        Users can directly pass in system_instructions. Or, we can generate system instructions by combining a
        persona_template and a persona.

        In these two cases, persona_template does not do anything since system_instructions is set directly or is None.
        - If system_instructions is already provided, we don't need to do anything since system_instructions is
        already set.
        - If neither system_instructions, persona, ideology, nor query_str is provided (default) set
        system_instructions to None.

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
            filtered_data = self._filter_data_by_ideology(self.ideology)
            if filtered_data.empty: raise AssertionError("No data found satisfying conditions")
            selected_row = filtered_data.sample(n=1, weights=filtered_data['weight']).iloc[0]
            return self._row2persona(selected_row, self.persona_mapping)
        elif self.query_str:
            filtered_data = self.data.query(self.query_str)
            if filtered_data.empty: raise AssertionError("No data found satisfying conditions")
            selected_row = filtered_data.sample(n=1, weights=filtered_data['weight']).iloc[0]
            return self._row2persona(selected_row, self.persona_mapping)

    def process(self, task: Optional[str] = None, previous_responses: str = "", ) -> Optional[str]:
        """
        Process the task, optionally building upon a previous response. If you pass in a task, it will replace the
        Agent's initialized task description. If you pass in a previous responses, it will be incorporated into the task
        description if combination_instructions are set via a Structure.

        Args:
            previous_responses (str): The previous responses to incorporate.
            task (Optional[str]): The task description to process. If not provided, the agent will use its current task.

        Returns:
            Optional[str]: The response from the LLM.
        """
        if task:
            self.set_task(task)

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

    def _filter_data_by_ideology(self, ideology: str) -> pd.DataFrame:
        """
        Filters the dataset based on the ideology.

        Args:
            ideology (str): The ideology to filter by.

        Returns:
            pd.DataFrame: The filtered dataset.
        """
        try:
            if ideology.lower() == 'liberal':
                return self.data[self.data['ideo5'].isin(['Liberal', 'Very liberal'])]
            elif ideology.lower() == 'conservative':
                return self.data[self.data['ideo5'].isin(['Conservative', 'Very conservative'])]
            elif ideology.lower() == 'moderate':
                return self.data[self.data['ideo5'] == 'Moderate']
            elif ideology.lower() == "very liberal":
                return self.data[self.data['ideo5'] == 'Very liberal']
            elif ideology.lower() == "very conservative":
                return self.data[self.data['ideo5'] == 'Very conservative']
            return pd.DataFrame()
        except Exception as e:
            raise AssertionError(f"Error filtering data by ideology: {e}")

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

        if self.system_instructions:
            assert not (self.persona_template != 'default' or self.persona), ("Cannot pass in system_instructions AND ("
                                                                              "persona_template or persona)")

        if self.ideology or self.query_str:
            assert not self.persona, "Cannot pass in (ideology or query_str) AND persona"

        if self.ideology:
            allowed_vals = ['liberal', 'conservative', 'moderate', 'very liberal', 'very conservative']
            assert self.ideology in allowed_vals, f"Ideology has to be one of: {str(allowed_vals)}"

    def _validate_templates(self):
        """
        Errors raised if:
        - a user passes in persona_template but it does not contain a persona placeholder (so there is no way to
        format it)
        """
        # if pass in persona_template, must contain persona placeholder
        if self.persona_template:
            default_templates = list(self.defaults['persona_template'].keys())

            assert '${persona}' in self.persona_template or self.persona_template in default_templates, ("If you pass "
                                                                                                         "in a "
                                                                                                         "persona_template, it must contain a ${persona} placeholder or be one of the default templates:") + str(
                default_templates)

    @property
    def history(self):
        if not self._history:
            warnings.warn("No history found. Please process a task first!")
            return None
        else:
            return self._history

    @property
    def info(self):
        return {"original_task": self.original_task_description,
                "current_task_description": self.current_task_description,
                "system_instructions": self.system_instructions, "history": self.history, "persona": self.persona,
                "ideology": self.ideology, "query_str": self.query_str, "model": self.model,
                "persona_template": self.persona_template, "kwargs": self.kwargs}

    def __repr__(self):
        return str(self.info)

    def set_task(self, task: str):
        """
        Set the task description for the agent to process.

        Args:
            task (str): The new task description.
        """
        self.original_task_description = task
        self.current_task_description = task
