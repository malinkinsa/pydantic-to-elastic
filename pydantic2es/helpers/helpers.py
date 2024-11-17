import os.path

from typing import List
from re import search

from pydantic2es.mappings.mappings_map import mappings_map


def is_path_available(path: str) -> bool:
    return bool(os.path.exists(path))

def get_mapping_value(key: str) -> dict:

    if 'Union' in key:
        param = search(r'\[(.*)\]', key).group(1)
        match param:
            case 'str, typing.List[dict], NoneType':
                return {"type": "object"}
            case _:
                return {"type": "keyword"}
    elif 'datetime' in key:
        return {"type": mappings_map.get(key, None), "ignore_malformed": True}

    else:
        return {"type": mappings_map.get(key, None)}

def _make_dict(converted_models: dict[dict[str, str]], parent_models: str, child_models_list: List[str]) \
        -> dict:
    data_dict = converted_models[parent_models]
    for key, value in data_dict.items():
        matching_child = next((child for child in child_models_list if child in value), None)
        if matching_child:
            data_dict[key] = converted_models[matching_child]

    return data_dict

def struct_dict(converted_models: dict[dict[str, str]]) -> List[dict[str, str]] | dict[str, dict[str, str]]:
    models_name = [converted_model_name for converted_model_name in converted_models]
    child_models_list = [
        model
        for model in models_name
        for sub_dict in converted_models.values()
        for value in sub_dict.values()
        if model in value
    ]

    parent_models_list = [
        converted_model_name for converted_model_name in converted_models
        if converted_model_name not in child_models_list
    ]

    if len(parent_models_list) == 1:
        return _make_dict(converted_models, parent_models_list[0], child_models_list)

    else:
        dicts_list = []
        for i in range(len(parent_models_list)):
            dicts_list.append(_make_dict(converted_models, parent_models_list[i], child_models_list))

        return dicts_list
