"""Convert resolved Pydantic 2 annotations to Elasticsearch mappings."""

from __future__ import annotations

import types
from collections.abc import Mapping, Sequence, Set as AbstractSet
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from inspect import isclass
from pathlib import Path
from typing import Annotated, Any, Literal, Union, get_args, get_origin
from uuid import UUID

from pydantic import BaseModel


class UnsupportedTypeError(TypeError):
    """Raised when an annotation has no unambiguous Elasticsearch mapping."""


def normalize_static_fields(
    static_fields: dict[str, list[str]] | None,
) -> dict[str, set[str]]:
    supported = {"text", "flattened"}
    normalized: dict[str, set[str]] = {key: set() for key in supported}
    for mapping_type, fields in (static_fields or {}).items():
        if mapping_type not in supported:
            raise ValueError(f"Unsupported static mapping type: {mapping_type}")
        normalized[mapping_type].update(field.strip() for field in fields if field.strip())

    conflicts = normalized["text"] & normalized["flattened"]
    if conflicts:
        raise ValueError(
            "Fields cannot be both text and flattened: " + ", ".join(sorted(conflicts))
        )
    return normalized


def _override_for(
    field_name: str,
    field_path: str,
    static_fields: dict[str, set[str]],
) -> str | None:
    matches = [
        mapping_type
        for mapping_type, fields in static_fields.items()
        if field_path in fields or field_name in fields
    ]
    if len(matches) > 1:
        raise ValueError(f"Conflicting mapping overrides for field {field_path}")
    return matches[0] if matches else None


def _unsupported(
    annotation: Any,
    field_path: str,
    reason: str = "",
) -> UnsupportedTypeError:
    suffix = f" ({reason})" if reason else ""
    return UnsupportedTypeError(
        f"Unsupported annotation for field '{field_path}': {annotation!r}{suffix}"
    )


def _literal_mapping(annotation: Any, field_path: str) -> dict[str, Any]:
    value_types = {type(value) for value in get_args(annotation)}
    if value_types <= {str}:
        return {"type": "keyword"}
    if value_types <= {bool}:
        return {"type": "boolean"}
    if value_types <= {int}:
        return {"type": "integer"}
    if value_types <= {int, float}:
        return {"type": "double"}
    raise _unsupported(annotation, field_path, "Literal values have incompatible types")


def _enum_mapping(annotation: type[Enum], field_path: str) -> dict[str, Any]:
    values = [member.value for member in annotation]
    if not values:
        raise _unsupported(annotation, field_path, "empty Enum")
    value_types = {type(value) for value in values}
    if value_types <= {str}:
        return {"type": "keyword"}
    if value_types <= {bool}:
        return {"type": "boolean"}
    if value_types <= {int}:
        return {"type": "integer"}
    if value_types <= {int, float}:
        return {"type": "double"}
    raise _unsupported(annotation, field_path, "Enum values have incompatible types")


def _model_properties(
    model: type[BaseModel],
    submodel_type: str,
    static_fields: dict[str, set[str]],
    parent_path: str,
    visiting: tuple[type[BaseModel], ...],
) -> dict[str, Any]:
    if model in visiting:
        cycle = " -> ".join(item.__name__ for item in (*visiting, model))
        raise _unsupported(model, parent_path or model.__name__, f"recursive model: {cycle}")

    properties: dict[str, Any] = {}
    next_visiting = (*visiting, model)
    for source_name, field in model.model_fields.items():
        output_name = field.serialization_alias or field.alias or source_name
        field_path = f"{parent_path}.{output_name}" if parent_path else output_name
        override = _override_for(output_name, field_path, static_fields)
        if override:
            properties[output_name] = {"type": override}
            continue
        properties[output_name] = _annotation_mapping(
            field.annotation,
            submodel_type,
            static_fields,
            field_path,
            next_visiting,
            in_collection=False,
        )
    return properties


def _annotation_mapping(
    annotation: Any,
    submodel_type: str,
    static_fields: dict[str, set[str]],
    field_path: str,
    visiting: tuple[type[BaseModel], ...],
    *,
    in_collection: bool,
) -> dict[str, Any]:
    if isinstance(annotation, str):
        referenced_name = annotation.strip("'\"")
        recursive_model = next(
            (
                model
                for model in reversed(visiting)
                if referenced_name in {model.__name__, model.__qualname__}
            ),
            None,
        )
        if recursive_model is not None:
            cycle = " -> ".join(
                model.__name__ for model in (*visiting, recursive_model)
            )
            raise _unsupported(
                annotation,
                field_path,
                f"recursive model: {cycle}",
            )
        raise _unsupported(annotation, field_path, "unresolved forward reference")

    origin = get_origin(annotation)
    arguments = get_args(annotation)

    if origin is Annotated:
        return _annotation_mapping(
            arguments[0],
            submodel_type,
            static_fields,
            field_path,
            visiting,
            in_collection=in_collection,
        )

    if origin in {Union, types.UnionType}:
        members = [member for member in arguments if member is not type(None)]
        if len(members) == 1:
            return _annotation_mapping(
                members[0],
                submodel_type,
                static_fields,
                field_path,
                visiting,
                in_collection=in_collection,
            )
        mappings = [
            _annotation_mapping(
                member,
                submodel_type,
                static_fields,
                field_path,
                visiting,
                in_collection=in_collection,
            )
            for member in members
        ]
        if mappings and all(mapping == mappings[0] for mapping in mappings[1:]):
            return mappings[0]
        numeric_types = {mapping.get("type") for mapping in mappings}
        if numeric_types <= {"integer", "float", "double"}:
            return {"type": "double"}
        raise _unsupported(annotation, field_path, "union members map to different types")

    if origin is Literal:
        return _literal_mapping(annotation, field_path)

    collection_origins = {list, set, frozenset, tuple, Sequence, AbstractSet}
    if origin in collection_origins:
        item_types = [argument for argument in arguments if argument is not Ellipsis]
        if not item_types:
            raise _unsupported(annotation, field_path, "collection item type is missing")
        item_mappings = [
            _annotation_mapping(
                item,
                submodel_type,
                static_fields,
                field_path,
                visiting,
                in_collection=True,
            )
            for item in item_types
        ]
        if not all(mapping == item_mappings[0] for mapping in item_mappings[1:]):
            raise _unsupported(
                annotation,
                field_path,
                "collection items map to different types",
            )
        return item_mappings[0]

    mapping_origins = {dict, Mapping}
    if origin in mapping_origins or annotation is dict:
        return {"type": "object"}

    if isclass(annotation) and issubclass(annotation, BaseModel):
        if submodel_type == "auto":
            object_type = "nested" if in_collection else "object"
        else:
            object_type = submodel_type
        return {
            "type": object_type,
            "properties": _model_properties(
                annotation, submodel_type, static_fields, field_path, visiting
            ),
        }

    if isclass(annotation) and issubclass(annotation, Enum):
        return _enum_mapping(annotation, field_path)

    if annotation is Any:
        return {"type": "object"}
    if annotation is str or (
        isclass(annotation) and issubclass(annotation, (UUID, Path))
    ):
        return {"type": "keyword"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "float"}
    if annotation is Decimal:
        return {"type": "double"}
    if annotation in {datetime, date}:
        return {"type": "date", "ignore_malformed": True}
    if annotation is bytes:
        return {"type": "binary"}

    raise _unsupported(annotation, field_path)


def model_to_mapping(
    model: type[BaseModel],
    submodel_type: str = "auto",
    static_fields: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Create a complete Elasticsearch mapping for one Pydantic model."""
    if submodel_type not in {"auto", "nested", "object"}:
        raise ValueError("submodel_type must be one of: auto, nested, object")
    if getattr(model, "__pydantic_root_model__", False):
        raise UnsupportedTypeError(
            f"RootModel {model.__name__} has no named fields and cannot be "
            "represented as Elasticsearch mapping properties"
        )
    normalized_fields = normalize_static_fields(static_fields)
    return {
        "mappings": {
            "properties": _model_properties(
                model, submodel_type, normalized_fields, "", ()
            )
        }
    }
