import yaml
from typing import List, Dict, Any

def print_values(mapping):
    for key in mapping.keys():
        vals = mapping[key]['values']
        if isinstance(vals, dict) and all(isinstance(v, dict) for v in vals.values()):
            for sub_key in vals.keys():
                sub_vals = vals[sub_key]
                sorted_sub_vals = dict(sorted(sub_vals.items(), key=lambda item: int(item[0]) if item[0].isdigit() else item[0]))
                print(f"{mapping[key]['name']} ({sub_key}):")
                for val_key, val in sorted_sub_vals.items():
                    if val:
                        print(f"  {val_key}: {val}")
        else:
            sorted_vals = dict(sorted(vals.items(), key=lambda item: int(item[0]) if item[0].lstrip('-').isdigit() else item[0]))
            print(mapping[key]['name'] + ":")
            for val_key, val in sorted_vals.items():
                print(f"  {key}=={val_key}: {val}")
        print()



def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    Load a YAML file and return its content as a dictionary.
    """
    with open(file_path, 'r') as file:
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

