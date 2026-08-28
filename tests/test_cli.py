import json

import pytest

from pydantic2es.main import main


def _model_file(tmp_path):
    path = tmp_path / "models.py"
    path.write_text(
        "from pydantic import BaseModel\n"
        "class Model(BaseModel):\n"
        "    title: str\n"
        "    metadata: dict\n",
        encoding="utf-8",
    )
    return path


def test_cli_parses_repeated_and_csv_overrides(tmp_path, capsys):
    model_file = _model_file(tmp_path)

    assert main([
        "--input", str(model_file),
        "--text_fields", "title,unused",
        "--flattened_fields", "metadata",
    ]) == 0

    output = json.loads(capsys.readouterr().out)
    properties = output["mappings"]["properties"]
    assert properties["title"] == {"type": "text"}
    assert properties["metadata"] == {"type": "flattened"}


def test_cli_writes_pretty_utf8_file(tmp_path):
    model_file = _model_file(tmp_path)
    output_file = tmp_path / "mapping.json"

    main([
        "--input", str(model_file),
        "--output", "file",
        "--output_path", str(output_file),
        "--output_format", "pretty",
    ])

    assert json.loads(output_file.read_text(encoding="utf-8"))["mappings"]
    assert "\n    " in output_file.read_text(encoding="utf-8")


def test_cli_accepts_flattened_field_without_text_fields(tmp_path, capsys):
    main([
        "--input", str(_model_file(tmp_path)),
        "--flattened_fields", "metadata",
    ])

    properties = json.loads(capsys.readouterr().out)["mappings"]["properties"]
    assert properties["metadata"] == {"type": "flattened"}


def test_cli_requires_output_path(tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        main(["--input", str(_model_file(tmp_path)), "--output", "file"])

    assert error.value.code == 2
    assert "--output_path is required" in capsys.readouterr().err
