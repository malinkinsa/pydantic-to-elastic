import textwrap

import pytest

from pydantic2es.converters.pydantic2dict import (
    ModelFileError,
    load_model_classes,
    select_model_classes,
)


def test_loader_finds_only_local_pydantic_models_and_supports_sibling_imports(tmp_path):
    (tmp_path / "adjacent_types.py").write_text("UserId = int\n", encoding="utf-8")
    model_file = tmp_path / "models.py"
    model_file.write_text(
        textwrap.dedent(
            """
            from pydantic import BaseModel
            from adjacent_types import UserId

            class Helper:
                pass

            class User(BaseModel):
                identifier: UserId
            """
        ),
        encoding="utf-8",
    )

    models = load_model_classes(model_file)

    assert list(models) == ["User"]
    assert models["User"].model_fields["identifier"].annotation is int


def test_selects_single_unreferenced_root(tmp_path):
    model_file = tmp_path / "models.py"
    model_file.write_text(
        textwrap.dedent(
            """
            from pydantic import BaseModel

            class Address(BaseModel):
                city: str

            class User(BaseModel):
                address: Address
            """
        ),
        encoding="utf-8",
    )
    models = load_model_classes(model_file)

    assert list(select_model_classes(models)) == ["User"]


def test_multiple_roots_require_model_selection(tmp_path):
    model_file = tmp_path / "models.py"
    model_file.write_text(
        "from pydantic import BaseModel\n"
        "class User(BaseModel):\n    name: str\n"
        "class Product(BaseModel):\n    name: str\n",
        encoding="utf-8",
    )
    models = load_model_classes(model_file)

    with pytest.raises(ModelFileError, match="--model"):
        select_model_classes(models)
    assert list(select_model_classes(models, ["Product"])) == ["Product"]


def test_missing_file_has_clear_error(tmp_path):
    with pytest.raises(ModelFileError, match="does not exist"):
        load_model_classes(tmp_path / "missing.py")
