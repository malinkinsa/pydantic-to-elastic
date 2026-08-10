# pydantic-to-elastic

A CLI and Python library that converts Pydantic 2 models into Elasticsearch
mappings.

## Installation

```bash
pip install pydantic-to-elastic
```

From source:

```bash
git clone https://github.com/malinkinsa/pydantic-to-elastic.git
cd pydantic-to-elastic
pip install .
```

For development:

```bash
pip install -e '.[test]'
pytest
```

## Usage

Given `user_models.py`:

```python
from datetime import datetime
from pydantic import BaseModel, Field


class Address(BaseModel):
    city: str
    zip_code: str


class User(BaseModel):
    name: str = Field(alias="displayName")
    address: Address
    previous_addresses: list[Address]
    created_at: datetime
```

Run:

```bash
pydantic2es --input ./user_models.py --output_format pretty
```

The single root model is detected automatically. Singular submodels become
`object` fields and collections of submodels become `nested` fields:

```json
{
    "mappings": {
        "properties": {
            "displayName": {"type": "keyword"},
            "address": {
                "type": "object",
                "properties": {
                    "city": {"type": "keyword"},
                    "zip_code": {"type": "keyword"}
                }
            },
            "previous_addresses": {
                "type": "nested",
                "properties": {
                    "city": {"type": "keyword"},
                    "zip_code": {"type": "keyword"}
                }
            },
            "created_at": {"type": "date", "ignore_malformed": true}
        }
    }
}
```

## CLI options

| Option | Description | Default |
|---|---|---|
| `--input PATH` | Python file containing Pydantic models; required | — |
| `--model NAME` | Root model to convert; repeat or comma-separate for several | auto-detect |
| `--output console\|file` | Output destination | `console` |
| `--output_path PATH` | Destination filename; required for file output | — |
| `--output_format json\|pretty` | Compact or indented JSON | `json` |
| `--submodel_type auto\|nested\|object` | Submodel mapping policy | `auto` |
| `--text_fields FIELD` | Force names or dotted paths to `text` | — |
| `--flattened_fields FIELD` | Force names or dotted paths to `flattened` | — |

Field options may be repeated or comma-separated:

```bash
pydantic2es \
  --input ./user_models.py \
  --text_fields displayName,address.city \
  --flattened_fields metadata
```

A bare field name applies at every nesting level. A dotted path such as
`address.city` applies only at that path. Assigning the same selector to both
`text` and `flattened` is an error.

When a file contains several independent root models, select one explicitly:

```bash
pydantic2es --input ./models.py --model User
```

If `--model` is repeated, the output is keyed by model name.

## Python API

```python
from pydantic2es import load_model_classes, model_to_mapping

models = load_model_classes("user_models.py")
mapping = model_to_mapping(models["User"])
```

Supported annotations include Pydantic submodels, optional fields, lists and
sets, dictionaries, `Literal`, string/numeric enums, `datetime`, `date`, UUID,
Decimal, bytes, and standard scalar types. Elasticsearch has no direct mapping
for every possible Python union or custom class; unsupported or ambiguous types
produce a descriptive error instead of emitting `"type": null`.

Recursive models are rejected because an Elasticsearch mapping must be finite.

## Security

The input Python file is imported and therefore executes its top-level code.
Only convert model files you trust.
