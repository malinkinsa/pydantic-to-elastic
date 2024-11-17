import sys

from importlib.util import spec_from_file_location, module_from_spec
from typing import get_origin, get_args, Union, Any
from uuid import uuid4
from inspect import isclass

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


def _model_to_dict(model_cls) -> dict:
    """
    Convert Pydantic to dict
    """
    if not hasattr(model_cls, "__annotations__"):
        raise TypeError(f"{model_cls} is not a Pydantic model or does not have annotations.")

    model_structure = {}
    for field_name, field_type in model_cls.__annotations__.items():
        model_structure[field_name] = _type_to_str(field_type)

    return model_structure


def _get_model_classes(path: str) -> dict[dict]:
    """
    Import pydantic models and return dict[name, class].
    """
    if is_path_available(path):
        uniq_name = uuid4().hex

        spec = spec_from_file_location(uniq_name, path)
        module = module_from_spec(spec)
        sys.modules[uniq_name] = module
        spec.loader.exec_module(module)

        available_classes = {
            name: cls
            for name, cls in vars(module).items()
            if isclass(cls) and cls.__module__ == uniq_name
        }

        result = _convert_model_classes_to_dict(available_classes)

        return result

    else:
        raise ValueError(f"Model file {path} is not exist.")

def _convert_model_classes_to_dict(model_classes: dict) -> dict:
    """
    Convert dict[ModelMetaclass] in to dict[dict].
    """
    return {name: _model_to_dict(cls) for name, cls in model_classes.items()}
