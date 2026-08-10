from typing import List

from pydantic2es.helpers.helpers import get_mapping_value


def _create_mapping(
    data: dict,
    submodel_type: str,
    static_fields: dict[str, List[str]],
    parent_path: str = "",
) -> dict:
    mapping = {
        "mappings": {
            "properties": {}
        }
    }

    for key, value in data.items():
        field_path = f"{parent_path}.{key}" if parent_path else key
        matched_types = [
            static_type
            for static_type, fields in static_fields.items()
            if key in fields or field_path in fields
        ]
        if len(matched_types) > 1:
            raise ValueError(f"Conflicting mapping overrides for field {field_path}")
        matched_type = matched_types[0] if matched_types else None

        if matched_type is not None:
            mapping["mappings"]["properties"][key] = {
                "type": matched_type
            }

        elif isinstance(value, dict):
            mapping["mappings"]["properties"][key] = {
                "type": "object" if submodel_type == "auto" else submodel_type,
                "properties": _create_mapping(
                    value, submodel_type, static_fields, field_path
                )["mappings"]["properties"]
            }

        else:
            mapping["mappings"]["properties"][key] = get_mapping_value(value)

    return mapping

def dict_to_mapping(
    converted_data: dict | List[dict],
    submodel_type: str,
    static_fields: dict[str, List[str]] | None = None,
    *,
    text_fields: List[str] | None = None,
) -> dict | List[dict]:
    """Convert the original dictionary representation.

    ``text_fields`` is retained as a deprecated compatibility argument. New code
    should pass ``static_fields``.
    """
    if static_fields is not None and text_fields is not None:
        raise ValueError("Pass either static_fields or text_fields, not both")
    if submodel_type not in {"auto", "nested", "object"}:
        raise ValueError("submodel_type must be one of: auto, nested, object")
    if static_fields is None:
        static_fields = {"text": text_fields or [], "flattened": []}
    unknown_types = set(static_fields) - {"text", "flattened"}
    if unknown_types:
        raise ValueError(f"Unsupported static mapping types: {', '.join(sorted(unknown_types))}")
    conflicts = set(static_fields.get("text", [])) & set(static_fields.get("flattened", []))
    if conflicts:
        raise ValueError(
            "Fields cannot be both text and flattened: " + ", ".join(sorted(conflicts))
        )
    if isinstance(converted_data, dict):
        return _create_mapping(converted_data, submodel_type, static_fields)
    else:
        return [_create_mapping(record, submodel_type, static_fields) for record in converted_data]
