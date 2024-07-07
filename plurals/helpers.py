import os
import string
from typing import List, Dict, Any

import yaml
import pkg_resources


def print_values(mapping):
    """
    Prints the values of ANES mapping in a human-readable format.

    Args:
        mapping: mapping (just ANEs supported for now)

    Returns:
        None

    Prints:
        The values of the ANES mapping in a neat/clean/human-readable way.
    """
    for key in mapping.keys():
        vals = mapping[key]['values']
        if isinstance(vals, dict) and all(isinstance(v, dict) for v in vals.values()):
            for sub_key in vals.keys():
                sub_vals = vals[sub_key]
                sorted_sub_vals = dict(
                    sorted(sub_vals.items(), key=lambda item: int(item[0]) if item[0].isdigit() else item[0]))
                print(f"{mapping[key]['name']} ({sub_key}):")
                for val_key, val in sorted_sub_vals.items():
                    if val:
                        print(f"  {val_key}: {val}")
        else:
            sorted_vals = dict(
                sorted(vals.items(), key=lambda item: int(item[0]) if item[0].lstrip('-').isdigit() else item[0]))
            print(mapping[key]['name'] + ":")
            for val_key, val in sorted_vals.items():
                print(f"  {key}=={val_key}: {val}")
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
