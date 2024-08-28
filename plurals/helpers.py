import os
import string
from typing import List, Dict, Any

import pandas as pd
import pkg_resources
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
    df = pd.read_csv(pkg_resources.resource_filename(
        __name__, 'data/anes_pilot_2024_20240319.csv'))
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
    full_path = pkg_resources.resource_filename(__name__, file_path)
    if not os.path.exists(full_path):
        raise FileNotFoundError(
            f"The file {full_path} does not exist. Please ensure the file path is correct.")

    with open(full_path, 'r') as file:
        return yaml.safe_load(file)


def format_previous_responses(responses: List[str]) -> str:
    """
    Format the previous responses for inclusion in the next task description.

    Args:
        responses (List[str]): A list of previous responses.

    Returns:
        str: A formatted string of the previous responses.

    Example:
        >>> responses = ["First response", "Second response"]
        >>> format_previous_responses(responses)
        'Response 0: First response\\nResponse 1: Second response'
    """
    if not responses:
        return ""
    else:
        resp_list = [
            "Response {}: {}\n".format(i, responses[i])
            for i in range(len(responses))
        ]
        return "".join(resp_list).strip()



class SmartString(str):
    """
    A custom string class that overrides the format method to use string.Template's safe substitute.

    Problem it fixes: Oftentimes users will have some kind of json type string in their task and this throws an error with
    normal strings.

    Longer explanation: The format method of Python's string class uses the curly braces syntax for string formatting. This
    breaks when the string `s` contains curly braces that are not meant to be replaced. So as a solution one can turn
    `s` into a string Template and use the ``safe_substitute`` method to replace the variables. This is what the
    SmartString class does: It is a subclass of string that overrides the format method to use ``string.Template`` for
    string formatting.
    """

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
        """
        if not self:
            return None
        template = string.Template(self)
        formatted_string = template.safe_substitute(**kwargs)
        if avoid_double_period:
            for key, value in kwargs.items():
                placeholder = f"${{{key}}}."
                if placeholder in self and value.endswith('.'):
                    formatted_string = formatted_string.replace(
                        f"{value}.", value)

        return formatted_string
