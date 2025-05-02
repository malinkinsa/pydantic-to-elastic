import importlib
import sys

from typing import get_origin, get_args, Union, Any
from inspect import isclass
from pathlib import Path

from pydantic2es.helpers.helpers import is_path_available


def models_to_dict(path: str):
    return _get_model_classes(path)

def _type_to_str(field_type: Any) -> str:
    """
    Convert type in str, include Optional, List, Set custom classes.
    """
    origin = get_origin(field_type)
    args = get_args(field_type)

    if origin is None:
        return field_type.__name__

    if origin in {list, set, dict}:
        arg_types = ", ".join(_type_to_str(arg) for arg in args)
        return f"{origin.__name__}[{arg_types}]"

    if origin is Union and len(args) == 2 and args[1] is type(None):
        return f"{_type_to_str(args[0])}"

    # Another types
    return str(field_type)


def _model_to_dict(model_cls, seen_models=None) -> dict:
    if seen_models is None:
        seen_models = {}

    if not hasattr(model_cls, "__annotations__"):
        raise TypeError(f"{model_cls} is not a Pydantic model or does not have annotations.")

    model_structure = {}
    for field_name, field_type in model_cls.__annotations__.items():
        try:
            type_str = _type_to_str(field_type)

            if type_str != "NoneType":
                model_structure[field_name] = type_str

                args = get_args(field_type)
                if hasattr(field_type, '__annotations__'):
                    seen_models[field_type.__name__] = _model_to_dict(field_type, seen_models)
                for arg in args:
                    if hasattr(arg, '__annotations__'):
                        seen_models[arg.__name__] = _model_to_dict(arg, seen_models)

        except Exception as e:
            print(f"Unexpected error for field {field_name}: {e}")
            continue

    return model_structure


def _get_model_classes(path: str) -> dict:
    """
    Import Pydantic models and return dict[name, class].
    """
    if not is_path_available(path):
        raise ValueError(f"Model file {path} does not exist.")

    abs_path = Path(path).resolve()
    module_dir = abs_path.parent
    module_name = abs_path.stem

    sys.path.insert(0, str(module_dir.parent))

    try:
        imported_module = importlib.import_module(module_name)

        available_classes = {
            name: cls
            for name, cls in vars(imported_module).items()
            if isclass(cls)
               and cls.__module__ == imported_module.__name__
        }

        result = _convert_model_classes_to_dict(available_classes)

        return result

    finally:
        if sys.path[0] == str(module_dir.parent):
            sys.path.pop(0)

def _convert_model_classes_to_dict(model_classes: dict) -> dict:
    result = {}
    seen_models = {}

    for name, cls in model_classes.items():
        model_dict = _model_to_dict(cls, seen_models)
        if model_dict:
            result[name] = model_dict

    for name, struct in seen_models.items():
        if name not in result and struct:
            result[name] = struct

    return result
