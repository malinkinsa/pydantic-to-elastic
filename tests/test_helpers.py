import pytest

from pydantic2es.helpers.helpers import struct_dict


@pytest.fixture
def converted_models():
    return {
        'Address': {
            'city': 'str',
            'street': 'str',
            'zip_code': 'str'
        },
        'User': {
            'name': 'str',
            'age': 'int',
            'address': 'Address',
            'hobbies': 'list[str]'
        }
    }


def test_struct_dict_user_address(converted_models):
    result = struct_dict(converted_models)

    assert isinstance(result, dict)
    assert isinstance(result["address"], dict)

    assert 'User' not in result
    assert "address" in result
    assert "city" in result["address"]
    assert "street" in result["address"]
    assert "zip_code" in result["address"]
    assert result["name"] == "str"
    assert result["age"] == "int"
    assert result["hobbies"] == "list[str]"