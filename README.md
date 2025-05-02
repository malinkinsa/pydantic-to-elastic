# pydantic-to-elastic

A simple CLI utility for converting Pydantic models to Elasticsearch mappings.

### Installation

#### From source
```bash
git clone https://github.com/malinkinsa/pydantic-to-elastic.git && cd pydantic-to-elastic
pip install .
```

### CLI options
| Prop               | Description                                                                                                                        | Required | Default value |
|:-------------------|:-----------------------------------------------------------------------------------------------------------------------------------|:---------|:--------------|
| --input            | Path to the file containing Pydantic models.                                                                                       | True     |               |
| --output           | Output type of result. Possible values: "console" or "file".                                                                       | False    | console       |
| --output_path      | Path and filename to save the output file (required if --output is set to 'file').                                                 | False    |               |
| --output_format    | Output format for JSON data. Use 'json' for compact single-line JSON or 'pretty' for pretty-printed JSON with 4-space indentation. | False    | json          |
| --submodel_type    | Specifies the submodel type. Possible values: "nested" or "object"                                                                 | False    | nested        |
| --text_fields      | List of fields that must be of type 'text'. Can be specified multiple times.                                                       | False    |               |               |
| --flattened_fields | List of fields that must be of type 'flattened'. Can be specified multiple times.                                                  | False    |               |

### Usage
For example, you have a model `user_models.py`
```python
from pydantic import BaseModel
from typing import List

class Address(BaseModel):
    street: str
    city: str
    zip_code: str

class User(BaseModel):
    name: str
    age: int
    address: Address
    hobbies: List[str]
```

Execute the command for converting these models into mapping json:
```bash
pydantic2es --input ./user_models.py --output_format pretty
```

And you will obtain the following result:
```json
{
    "mappings": {
        "properties": {
            "name": {
                "type": "keyword"
            },
            "age": {
                "type": "integer"
            },
            "address": {
                "type": "nested",
                "properties": {
                    "street": {
                        "type": "keyword"
                    },
                    "city": {
                        "type": "keyword"
                    },
                    "zip_code": {
                        "type": "keyword"
                    }
                }
            },
            "hobbies": {
                "type": "keyword"
            }
        }
    }
}
```
