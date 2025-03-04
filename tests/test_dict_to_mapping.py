import pytest

from pydantic2es.converters.dict2mapping import dict_to_mapping


@pytest.fixture
def sample_data():
    return {
        'address': {
            'city': 'str', 'street': 'str', 'zip_code': 'str'
        },
        'age': 'int',
        'hobbies':
            'list[str]',
        'name': 'str'
    }

def test_dict_to_mapping(sample_data):
    submodel_type = 'object'

    mapping = dict_to_mapping(sample_data, submodel_type, text_fields=[])

    expected_mapping = {
        "mappings": {
            "properties": {
                "name": {
                    "type": "keyword"
                },
                "age": {
                    "type": "integer"
                },
                "address": {
                    "type": "object",
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


    assert mapping == expected_mapping
