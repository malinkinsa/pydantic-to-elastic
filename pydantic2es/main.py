import json

from argparse import ArgumentParser, RawTextHelpFormatter, Namespace
from pathlib import Path
from typing import List
from sys import stdout

from pydantic2es.converters.dict2mapping import dict_to_mapping
from pydantic2es.converters.pydantic2dict import models_to_dict
from pydantic2es.helpers.helpers import struct_dict


def _parse_cli_args(args: List[str] = None) -> Namespace:
    """
    Parses command-line arguments for the pydantic2elastic utility.
    """
    parser = ArgumentParser(
        prog="pydantic2es",
        description='Utility for converting Pydantic models to Elasticsearch mappings.',
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to the file containing Pydantic models."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="console",
        choices=["console", "file"],
        help='Output type of result. Possible values: "console" (default) or "file".',
    )
    parser.add_argument(
        "--output_path",
        type=str,
        help="Path and filename to save the output file (required if --output is set to 'file').",
    )
    parser.add_argument(
        '--output_format',
        type=str,
        choices=['json', 'pretty'],
        default='json',
        help=(
            "Output format for JSON data. "
            "Use 'json' for compact single-line JSON (default) or 'pretty' for pretty-printed JSON with 4-space "
            "indentation."
        )
    )
    parser.add_argument(
        "--submodel_type",
        type=str,
        default="nested",
        choices=["nested", "object"],
        help='Specifies the submodel type. Possible values: "nested" (default) or "object".',
    )
    parser.add_argument(
        "--text_fields",
        type=str,
        action="append",
        default=[],
        help="List of fields that must be of type 'text'. Can be specified multiple times.",
    )
    parser.add_argument(
        "--flattened_fields",
        type=str,
        action="append",
        default=[],
        help="List of fields that must be of type 'flattened'. Can be specified multiple times.",
    )

    return parser.parse_args(args)

def _check_args(args: Namespace) -> None:
    if 'file' in args.output and not args.output_path:
        raise ValueError("--output_path is required when --output is set to 'file'.")

def main() -> None:
    args = _parse_cli_args()
    _check_args(args)

    if len(args.text_fields) == 1 and ',' in args.text_fields[0]:
        args.text_fields = args.text_fields[0].split(',')

    if len(args.flattened_fields) == 1 and ',' in args.text_fields[0]:
        args.flattened_fields = args.flattened_fields[0].split(',')

    static_fields = {
        'text': args.text_fields,
        'flattened': args.flattened_fields,
    }

    mapping_data = dict_to_mapping(
        struct_dict(models_to_dict(args.input)),
        args.submodel_type,
        static_fields
    )

    output_data = (
        json.dumps(mapping_data, indent=4)
        if "pretty" in args.output_format
        else json.dumps(mapping_data)
    )

    match args.output:
        case "console":
            stdout.write(output_data)
        case "file":
            output_path = Path(args.output_path).resolve()
            with open(output_path, 'w') as file:
                file.write(output_data)

if __name__ == "__main__":
    main()
