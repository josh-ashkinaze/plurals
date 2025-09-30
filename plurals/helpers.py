import os
import string
from typing import List, Dict, Any, Optional

import pandas as pd
import yaml


def print_anes_mapping():
    """
    Prints the values of ANES mapping in a human-readable format.

    The purpose of this function is that in some cases users will want to conduct their own query on the ANES
    dataset, but it is difficult to know what the values are without consulting a codebook.

    Note that when generating personas we recode certain values but you should use original
    values for filtering data, as they are printed here.

    Here are the cases we recode values:

    - ``child18`` asks participants if they have children under 18 living in their household. We recode ``Yes`` to ``do have
      children under 18 living in your household`` and ``No`` to ``do not have children under 18 living in your household``.

    - Several questions have multiple choice options (A, B, C) and then an ``Other`` option. We recode ``Other``
      as ``neither A nor B nor C`` to be more explicit.


    """
    mapping = load_yaml('anes-mapping.yaml')
    df = pd.read_csv(get_resource_path(__name__, 'data/anes_pilot_2024_20240319.csv'))
    for key in mapping.keys():
        details = mapping[key]

        print(f"ANES Variable Name: {key}")

        bad_vals = details.get('bad_vals', set())

        # Print the main values from the DataFrame, excluding those that are
        # in bad_vals
        if key in df.columns:
            values = df[key].unique()
            for val in values:
                if str(val) not in bad_vals and str(val) != "nan":
                    print(f"{val}")
        print()


def strip_nested_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strip whitespace from all strings in a nested dictionary.

    Args:
        d: The dictionary to strip whitespace from.

    Returns:
        The dictionary with all strings stripped of whitespace.
    """
    if isinstance(d, dict):
        return {k: strip_nested_dict(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [strip_nested_dict(v) for v in d]
    elif isinstance(d, str):
        return d.strip()
    else:
        return d


def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    Load a YAML file and return its content as a dictionary. We first get the directory of the current path
    and then construct the full path by combining the base_path with the file_path. Hence, the file_path should be
    relative to this script's location.

    Args:
        file_path: The path to the YAML file to load.

    Returns:
        A dictionary containing the contents of the YAML file.
    """
    full_path = get_resource_path(__name__, file_path)
    if not os.path.exists(full_path):
        raise FileNotFoundError(
            f"The file {full_path} does not exist. Please ensure the file path is correct.")

    with open(full_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)


def format_previous_responses(responses: List[str], agent_names: Optional[List[str]] = None) -> str:
    """
    Format the previous responses for inclusion in the next task description.

    Args:
        responses (List[str]): A list of previous responses.
        agent_names (Optional[List[str]]): Optional list of agent names/identifiers corresponding to each response.

    Returns:
        str: A formatted string of the previous responses.

    Example:
        >>> responses = ["First response", "Second response"]
        >>> format_previous_responses(responses)
        'Response 0: First response\\nResponse 1: Second response'

        >>> format_previous_responses(responses, agent_names=["Agent A", "Agent B"])
        'Agent A: First response\\nAgent B: Second response'
    """
    if not responses:
        return ""
    else:
        if agent_names and len(agent_names) == len(responses):
            resp_list = [
                "{}: {}\n".format(agent_names[i], responses[i])
                for i in range(len(responses))
            ]
        else:
            resp_list = [
                "Response {}: {}\n".format(i, responses[i])
                for i in range(len(responses))
            ]
        return "".join(resp_list).strip()


class SmartString(str):
    """
    A custom string class with several nice features for this package.

    Features
    --------


    1. Safe String Formatting
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    Overrides the format method to use ``safe_substitute`` from ``string.Template``.

    Problem it fixes:
        Users often have JSON-like strings in their tasks, which can cause errors with normal string formatting.

    Explanation:
        Python's standard string formatting uses curly braces, which can break when the string contains curly braces NOT meant for replacement.
        SmartString uses ``string.Template.safe_substitute()`` to safely replace variables, avoiding these problems.

    2. Avoid Double Periods
    ~~~~~~~~~~~~~~~~~~~~~~~
    Prevents double periods at the end of formatted strings.

    Problem it fixes:
        When a replacement value ends with a period and the original string also ends with a period, it results in an undesired double period.

    Example:
        >>> task = SmartString("Complete the following task: {task}.")
        >>> task.format(task="Do the thing.")
        'Complete the following task: Do the thing.'

        **Without** this feature, the output would be:
        'Complete the following task: Do the thing..'

    3. None Replacement
    ~~~~~~~~~~~~~~~~~~~
    Replaces 'None' with an empty string during string creation.

    Problem it fixes:
        ``str(None)`` returns the string 'None', but for the ``Agent.process`` function, it's preferable to replace 'None' with an empty string.

    Example:
        >>> SmartString(None)
        ''
        >>> str(None)
        'None'

    Notes
    -----
    - The `format` method uses `string.Template.safe_substitute()` internally.
    - Double periods are automatically avoided unless specified otherwise.
    - 'None' is replaced with an empty string during string creation.
    """

    def __new__(cls, content):
        # Replace 'None' with an empty string during string creation
        if isinstance(content, str):
            content = content.replace('None', '')
        return super().__new__(cls, content)

    def format(self, avoid_double_period=True, **kwargs):
        """
        Override the format method to use string.Template for string formatting.

        Also, if ``avoid_double_period`` is True, then we will remove the trailing period from the formatted string if it
        is already present. This happens if the string is like `Complete the following task: {task}.` and the user passes `task=Do
        the thing`. In this case, the default output would have an extra period: `Complete the following task: Do the thing..`

        Double-period algorithm:

        Foreach key, value in kwargs:

        1. Construct a placeholder-plus-period like "{task}." (assuming {task} is placeholder here)

        2. Check if the placeholder-plus-period is in the string AND the replacement ends with a period.

        3. If both conditions are met, replace the replacement-plus-period with just the replacement.

        Args:
            avoid_double_period (bool): Whether to avoid double periods in the final string. (Default: True)
            **kwargs: Key-value pairs to replace in the string.
        Returns:
            str: The formatted string.

        Notes:
            - In edge case where the value for a key is None, we replace it with an empty string. Example of this:
            >>> task = SmartString("Complete the following task: {task}.")
            >>> task.format(task=None)
            'Complete the following task: .'

        """
        if not self:
            return None

        kwargs = {k: ('' if v is None else v) for k, v in kwargs.items()}

        template = string.Template(self)
        formatted_string = template.safe_substitute(**kwargs)
        if avoid_double_period:
            for key, value in kwargs.items():
                placeholder = f"${{{key}}}."
                if placeholder in self and value.endswith('.'):
                    formatted_string = formatted_string.replace(
                        f"{value}.", value)

        return formatted_string


def get_resource_path(package: str, resource: str) -> str:
    """Get the path to a resource file, supporting both pkg_resources and importlib.resources.
    Falls back to importlib.resources if pkg_resources is not available.

    Problem this solves:
        - In python 3.12, pkg_resources is being deprecated in favor of importlib.resources, and
          it no longer comes with pkg_resources. This creates an import error unless user does
          `pip install setuptools` but it is bad practice to add setuptools as a runtime dependency.
        - If I just switch to importlib, this is limiting since importlib is only for 3.9+.
        - So the solution is to use pkg_resources if available, and if not, use importlib.resources.

    Args:
        package (str): The package name (just __name__ usually)
        resource (str): The resource path relative to the package
    """
    try:
        import pkg_resources
        return pkg_resources.resource_filename(package, resource)
    except ImportError:
        from importlib import resources
        root_package = package.split('.')[0]
        with resources.path(root_package, resource) as path:
            return str(path)