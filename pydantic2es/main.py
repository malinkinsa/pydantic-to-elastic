"""Command-line interface for pydantic-to-elastic."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter
from pathlib import Path
from typing import Sequence

from pydantic2es.converters.pydantic2dict import (
    ModelFileError,
    load_model_classes,
    select_model_classes,
)
from pydantic2es.converters.pydantic2mapping import (
    UnsupportedTypeError,
    model_to_mapping,
)


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="pydantic2es",
        description="Convert Pydantic 2 models to Elasticsearch mappings.",
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to the Python file containing Pydantic models.",
    )
    parser.add_argument(
        "--model",
        type=str,
        action="append",
        default=[],
        help=(
            "Model to convert. Required when the file has multiple root models; "
            "may be repeated or comma-separated."
        ),
    )
    parser.add_argument(
        "--output",
        type=str,
        default="console",
        choices=["console", "file"],
        help='Output destination: "console" (default) or "file".',
    )
    parser.add_argument(
        "--output_path",
        type=str,
        help="Destination filename; required with --output file.",
    )
    parser.add_argument(
        "--output_format",
        type=str,
        choices=["json", "pretty"],
        default="json",
        help='Use "json" for compact output or "pretty" for indented output.',
    )
    parser.add_argument(
        "--submodel_type",
        type=str,
        default="auto",
        choices=["auto", "nested", "object"],
        help=(
            'Mapping for submodels. "auto" (default) maps a model to object and '
            "a collection of models to nested."
        ),
    )
    parser.add_argument(
        "--text_fields",
        type=str,
        action="append",
        default=[],
        help="Fields forced to text; names or dotted paths, repeated or comma-separated.",
    )
    parser.add_argument(
        "--flattened_fields",
        type=str,
        action="append",
        default=[],
        help=(
            "Fields forced to flattened; names or dotted paths, repeated or "
            "comma-separated."
        ),
    )
    return parser


def _parse_cli_args(args: Sequence[str] | None = None) -> Namespace:
    return _build_parser().parse_args(args)


def _split_values(values: Sequence[str]) -> list[str]:
    return [
        item.strip()
        for value in values
        for item in value.split(",")
        if item.strip()
    ]


def _check_args(args: Namespace) -> None:
    if args.output == "file" and not args.output_path:
        raise ValueError("--output_path is required when --output is set to 'file'.")
    if args.output == "console" and args.output_path:
        raise ValueError("--output_path can only be used with --output file.")


def build_mapping(args: Namespace) -> dict:
    """Build output data from parsed CLI arguments; separated for testability."""
    _check_args(args)
    models = load_model_classes(args.input)
    selected = select_model_classes(models, _split_values(args.model))
    static_fields = {
        "text": _split_values(args.text_fields),
        "flattened": _split_values(args.flattened_fields),
    }
    mappings = {
        name: model_to_mapping(model, args.submodel_type, static_fields)
        for name, model in selected.items()
    }
    return next(iter(mappings.values())) if len(mappings) == 1 else mappings


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        mapping_data = build_mapping(args)
    except (ModelFileError, UnsupportedTypeError, TypeError, ValueError) as exc:
        parser.error(str(exc))

    output_data = json.dumps(
        mapping_data,
        indent=4 if args.output_format == "pretty" else None,
        ensure_ascii=False,
    )
    if args.output == "console":
        sys.stdout.write(output_data + "\n")
    else:
        output_path = Path(args.output_path).expanduser().resolve()
        output_path.write_text(output_data + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
