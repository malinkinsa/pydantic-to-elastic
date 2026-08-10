"""Loading and inspecting Pydantic models from a Python source file."""

from __future__ import annotations

import importlib.util
import sys
import types
from collections.abc import Iterable
from inspect import isclass
from pathlib import Path
from typing import Any, ForwardRef, Union, get_args, get_origin
from uuid import uuid4

from pydantic import BaseModel


class ModelFileError(ValueError):
    """Raised when a model file cannot provide usable Pydantic models."""


def _module_identity(path: Path) -> tuple[str, Path]:
    """Return an import name and the directory that must be on ``sys.path``.

    Package-qualified names preserve relative imports. Standalone files receive a
    unique module name so that two files named ``models.py`` cannot share the
    import cache.
    """
    package_parts: list[str] = []
    parent = path.parent
    while (parent / "__init__.py").is_file():
        package_parts.append(parent.name)
        parent = parent.parent

    if package_parts:
        package = ".".join(reversed(package_parts))
        return f"{package}.{path.stem}", parent

    return f"_pydantic2es_{path.stem}_{uuid4().hex}", path.parent


def load_model_classes(path: str | Path) -> dict[str, type[BaseModel]]:
    """Load locally declared ``BaseModel`` subclasses from *path*.

    The model module is executed, exactly as with a normal Python import. Callers
    should therefore only convert trusted model files.
    """
    model_path = Path(path).expanduser().resolve()
    if not model_path.is_file():
        raise ModelFileError(f"Model file does not exist or is not a file: {model_path}")
    if model_path.suffix != ".py":
        raise ModelFileError(f"Model file must have a .py extension: {model_path}")

    module_name, import_root = _module_identity(model_path)
    spec = importlib.util.spec_from_file_location(module_name, model_path)
    if spec is None or spec.loader is None:
        raise ModelFileError(f"Unable to create an import specification for {model_path}")

    module = importlib.util.module_from_spec(spec)
    previous_module = sys.modules.get(module_name)
    sys.modules[module_name] = module
    sys.path.insert(0, str(import_root))
    try:
        spec.loader.exec_module(module)
    except Exception:
        if previous_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module
        raise
    finally:
        try:
            sys.path.remove(str(import_root))
        except ValueError:
            pass

    models = {
        name: cls
        for name, cls in vars(module).items()
        if isclass(cls)
        and cls.__module__ == module.__name__
        and issubclass(cls, BaseModel)
        and cls is not BaseModel
    }
    if not models:
        raise ModelFileError(f"No Pydantic BaseModel subclasses found in {model_path}")

    for model in models.values():
        try:
            model.model_rebuild(force=True)
        except Exception as exc:
            raise ModelFileError(
                f"Unable to resolve annotations for model {model.__name__}: {exc}"
            ) from exc
    return models


def iter_model_types(annotation: Any) -> Iterable[type[BaseModel]]:
    """Yield Pydantic models referenced anywhere inside an annotation."""
    if isclass(annotation) and issubclass(annotation, BaseModel):
        yield annotation
        return
    for argument in get_args(annotation):
        if argument is not type(None):
            yield from iter_model_types(argument)


def select_model_classes(
    models: dict[str, type[BaseModel]],
    requested: Iterable[str] | None = None,
) -> dict[str, type[BaseModel]]:
    """Select requested models or infer the single unreferenced root model."""
    requested_names = list(requested or [])
    if requested_names:
        unknown = [name for name in requested_names if name not in models]
        if unknown:
            available = ", ".join(models)
            raise ModelFileError(
                f"Unknown model(s): {', '.join(unknown)}. Available models: {available}"
            )
        return {name: models[name] for name in dict.fromkeys(requested_names)}

    referenced = {
        referenced_model
        for model in models.values()
        for field in model.model_fields.values()
        for referenced_model in iter_model_types(field.annotation)
        if referenced_model in models.values() and referenced_model is not model
    }
    roots = {name: model for name, model in models.items() if model not in referenced}
    if len(roots) == 1:
        return roots
    if len(models) == 1:
        return models

    candidates = roots or models
    raise ModelFileError(
        "Multiple root models found: "
        f"{', '.join(candidates)}. Select one or more with --model."
    )


def _type_to_str(field_type: Any) -> str:
    """Legacy, lossless-enough representation used by ``models_to_dict``."""
    if isinstance(field_type, str):
        return field_type
    if isinstance(field_type, ForwardRef):
        return field_type.__forward_arg__
    if field_type is type(None):
        return "NoneType"

    origin = get_origin(field_type)
    args = get_args(field_type)
    if origin is None:
        return getattr(field_type, "__name__", str(field_type))
    if origin in {Union, types.UnionType}:
        non_null = [argument for argument in args if argument is not type(None)]
        if len(non_null) == 1:
            return _type_to_str(non_null[0])
    origin_name = getattr(origin, "__name__", str(origin).replace("typing.", ""))
    return f"{origin_name}[{', '.join(_type_to_str(argument) for argument in args)}]"


def _model_to_dict(
    model_cls: type[BaseModel],
    seen_models: dict[str, dict[str, str]] | None = None,
    visiting: set[type[BaseModel]] | None = None,
) -> dict[str, str]:
    """Compatibility representation of a model's fields.

    New conversion code consumes ``model_fields`` directly. This function remains
    available for callers of the original library API.
    """
    seen_models = {} if seen_models is None else seen_models
    visiting = set() if visiting is None else visiting
    if model_cls in visiting:
        return {}

    visiting.add(model_cls)
    structure: dict[str, str] = {}
    for field_name, field in model_cls.model_fields.items():
        output_name = field.serialization_alias or field.alias or field_name
        structure[output_name] = _type_to_str(field.annotation)
        for nested_model in iter_model_types(field.annotation):
            if nested_model is model_cls or nested_model.__name__ in seen_models:
                continue
            seen_models[nested_model.__name__] = _model_to_dict(
                nested_model, seen_models, visiting
            )
    visiting.remove(model_cls)
    return structure


def _convert_model_classes_to_dict(
    model_classes: dict[str, type[BaseModel]],
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    seen_models: dict[str, dict[str, str]] = {}
    for name, model in model_classes.items():
        result[name] = _model_to_dict(model, seen_models)
    for name, structure in seen_models.items():
        result.setdefault(name, structure)
    return result


def models_to_dict(path: str | Path) -> dict[str, dict[str, str]]:
    """Compatibility wrapper returning the original string-based structure."""
    return _convert_model_classes_to_dict(load_model_classes(path))


# Kept for compatibility with the original private function name.
_get_model_classes = models_to_dict
