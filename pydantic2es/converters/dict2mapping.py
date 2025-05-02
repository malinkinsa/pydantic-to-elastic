from typing import List

from pydantic2es.helpers.helpers import get_mapping_value


def _create_mapping(data: dict, submodel_type: str, static_fields: dict[str, List[str]]) -> dict:
    mapping = {
        "mappings": {
            "properties": {}
        }
    }

    for key, value in data.items():
        matched_type = next(
            (static_type for static_type, fields in static_fields.items() if key in fields),
            None
        )

        if matched_type is not None:
            mapping["mappings"]["properties"][key] = {
                "type": matched_type
            }

        elif isinstance(value, dict):
            mapping["mappings"]["properties"][key] = {
                "type": submodel_type,
                "properties": _create_mapping(value, submodel_type, static_fields)["mappings"]["properties"]
            }

        else:
            mapping["mappings"]["properties"][key] = get_mapping_value(value)

    return mapping

def dict_to_mapping(converted_data: dict | List[dict], submodel_type: str, static_fields: dict[str, List[str]]) \
        -> dict | List[dict]:
    if isinstance(converted_data, dict):
        return _create_mapping(converted_data, submodel_type, static_fields)
    else:
        return [_create_mapping(record, submodel_type, static_fields) for record in converted_data]
