import os
import string
from typing import List, Dict, Any

import yaml
import pkg_resources

import pandas as pd


def print_anes_mapping():
    """
    Prints the values of ANES mapping in a human-readable format.

    The purpose of this function is that in some cases users will want to conduct their own query on the ANES dataset, but
    it is difficult to know what the values are without consulting a codebook. We also recode certain values. So here we
    print the values of the ANES mapping in a neat/clean/human-readable way for consumer.

    Note: Whenever we print `recode values` this means that we have recoded the values from the original dataset to use in persona strings. For example,
    for `child18`, the question was whether the participant has children under 18 living in their household. For persona processing, we changed
    `Yes` and `No` to `do have children under 18 living in your household` and `do not have children under 18 living in your household`---though to
    search ANES you'd use the original values. of `Yes` and `No`.
    """
    mapping = load_yaml('anes-mapping.yaml')
    df = pd.read_csv(pkg_resources.resource_filename(__name__, 'data/anes_pilot_2024_20240319.csv'))
    for key in mapping.keys():
        details = mapping[key]
        clean_name = details.get('name', '')
        var_name = details.get('clean_var', '')

        print(f"ANES Variable Name: {key}")

        # Handle recode_vals
        recode_vals = details.get('recode_vals', {})
        recode_keys = set(recode_vals.keys())
        if recode_vals:
            print(f"{clean_name} (recode values):")
            for val_key, val in recode_vals.items():
                print(f"  {val_key}: {val}")

        # Skip printing bad_vals
        bad_vals = details.get('bad_vals', set())

        # Print the main values from the DataFrame, excluding those that are recode values
        print(f"Persona string: `{clean_name}`:")
        if key in df.columns:
            values = df[key].unique()

            # If it's the case that all values are recoded don't double print
            if df[key].nunique() <= len(recode_keys):
                pass
            else:
                for val in values:
                    if str(val) not in bad_vals and str(val) not in recode_keys:
                        print(f"  {val}")
        print()



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
        raise FileNotFoundError(f"The file {full_path} does not exist. Please ensure the file path is correct.")

    with open(full_path, 'r') as file:
        return yaml.safe_load(file)


def format_previous_responses(responses: List[str]) -> str:
    """
    Format the previous responses for inclusion in the next task description.

    Args:
        responses: A list of previous responses.

    Returns:
        A formatted string of the previous responses. By default, strings are formatted like:
        Response 0: response0
        Response 1: response1
    """
    if not responses:
        return ""
    else:
        resp_list = ["Response {}: {}\n".format(i, responses[i]) for i in range(len(responses))]
        return "".join(resp_list)


class SmartString(str):
    """
    A custom string class that overrides the format method to use string.Template's safe substitute.

    Problem it fixes: Oftentimes users will have some kind of json string in their task and this throws an error with
    normal strings.

    Longer explanation: The format method of the str class uses the curly braces syntax for string formatting. This
    breaks when the string contains curly braces that are not meant to be replaced. For example:

    s = "Hello, {name} I am a json like {'key':'value'}"
    new_s = s.format(name="John")

    This will raise a KeyError because the format method will try to replace the curly braces in the json string as well, but we
    only want to replace {name}. So as a solution one can turn `s` into a string Template and use the safe_substitute method to
    replace the variables. This is what the SmartString class does: It is a subclass of str that overrides the format method to
    use string.Template for string formatting.
    """

    def format(self, **kwargs):
        """
        Override the format method to use string.Template for string formatting.
        """
        template = string.Template(self)
        return template.safe_substitute(**kwargs)
