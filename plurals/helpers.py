import yaml
from typing import List, Dict, Any
import os


def print_values(mapping):
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
    Load a YAML file and return its content as a dictionary.

    The file_path should be relative to this script's location.
    """
    # Get the directory of the current script
    base_path = os.path.dirname(os.path.abspath(__file__))
    # Construct the full path by combining base_path with file_path
    full_path = os.path.join(base_path, file_path)

    with open(full_path, 'r') as file:
        return yaml.safe_load(file)


def format_previous_responses(responses: List[str]) -> str:
    """
    Format the previous responses for inclusion in the next task description.
    """
    if not responses:
        return ""
    else:
        resp_list = ["Response {}: {}\n".format(i, responses[i]) for i in range(len(responses))]
        return "".join(resp_list)


def get_fromdict_bykey_or_alternative(dictvalue: Dict[str, Any], option: str, alternative: str):
    values = list(dictvalue.keys())
    for item in values:
        if item == option:
            # found matching in dict, return it
            return dictvalue[option]
        else:
            pass
    # if not foudn in dict, return alternative
    return alternative
