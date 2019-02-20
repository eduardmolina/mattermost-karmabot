import json


def json_to_dict(json_path):
    d = {}
    with open(json_path, 'r') as j:
        d = json.load(j)

    return d
