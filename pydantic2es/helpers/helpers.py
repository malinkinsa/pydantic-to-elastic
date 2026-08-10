import os.path

from typing import List
from re import search

from pydantic2es.mappings.mappings_map import mappings_map


def is_path_available(path: str) -> bool:
    return bool(os.path.exists(path))

def get_mapping_value(key: str) -> dict:

    if 'Union' in key:
        matched = search(r'\[(.*)\]', key)
        if matched is None:
            raise ValueError(f"Malformed Union annotation: {key}")
        param = matched.group(1)
        match param:
            case 'str, typing.List[dict], NoneType':
                return {"type": "object"}
            case _:
                raise TypeError(f"Unsupported Union annotation: {key}")
    elif 'datetime' in key:
        mapping_type = mappings_map.get(key)
        if mapping_type is None:
            raise TypeError(f"Unsupported field type: {key}")
        return {"type": mapping_type, "ignore_malformed": True}

    else:
        mapping_type = mappings_map.get(key)
        if mapping_type is None:
            raise TypeError(f"Unsupported field type: {key}")
        return {"type": mapping_type}

def _make_dict(
    converted_models: dict[str, dict[str, str]],
    parent_model: str,
    child_models_list: List[str],
    visiting: tuple[str, ...] = (),
) -> dict:
    if parent_model in visiting:
        cycle = " -> ".join((*visiting, parent_model))
        raise ValueError(f"Recursive model cannot be expanded: {cycle}")
    next_visiting = (*visiting, parent_model)
    data_dict = converted_models[parent_model].copy()

    for key, value in data_dict.items():
        if value in child_models_list:
            data_dict[key] = _make_dict(
                converted_models, value, child_models_list, next_visiting
            )
        elif isinstance(value, str):
            container_match = search(r"^(?:list|set|frozenset|tuple)\[([^,\]]+)", value)
            if container_match and container_match.group(1) in converted_models:
                child_name = container_match.group(1)
                data_dict[key] = _make_dict(
                    converted_models, child_name, child_models_list, next_visiting
                )

    return data_dict


def _referenced_model_name(value: object, model_names: set[str]) -> str | None:
    if isinstance(value, str) and value in model_names:
        return value
    if not isinstance(value, str):
        return None
    container_match = search(r"^(?:list|set|frozenset|tuple)\[([^,\]]+)", value)
    if container_match and container_match.group(1) in model_names:
        return container_match.group(1)
    return None


def struct_dict(
    converted_models: dict[str, dict[str, str]],
) -> List[dict[str, str]] | dict[str, dict[str, str]]:
    model_names = set(converted_models)
    child_models_list = [
        child_name
        for sub_dict in converted_models.values()
        for value in sub_dict.values()
        if (child_name := _referenced_model_name(value, model_names)) is not None
    ]

    parent_models_list = [
        converted_model_name for converted_model_name in converted_models
        if converted_model_name not in child_models_list
    ]

    if converted_models and not parent_models_list:
        raise ValueError("No root model found; model references are recursive")

    if len(parent_models_list) == 1:
        return _make_dict(converted_models, parent_models_list[0], child_models_list)

    else:
        dicts_list = []
        for i in range(len(parent_models_list)):
            dicts_list.append(
                _make_dict(
                    converted_models,
                    parent_models_list[i],
                    child_models_list,
                )
            )

        return dicts_list
