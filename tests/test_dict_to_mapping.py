import pytest

from pydantic2es.converters.dict2mapping import dict_to_mapping


@pytest.fixture
def first_sample():
    return {
        'address': {
            'city': 'str', 'street': 'str', 'zip_code': 'str'
        },
        'age': 'int',
        'hobbies':
            'list[str]',
        'name': 'str'
    }

@pytest.fixture
def second_sample():
    return {
        'user': {
            'name': 'str',
            'age': 'int',
            'address': {
                'city': 'str',
                'street': 'str',
                'zip_code': 'str',
                'geo': {
                    'latitude': 'float',
                    'longitude': 'float'
                }
            },
            'hobbies': 'list[str]'
        }
    }

def test_dict_to_mapping(first_sample, second_sample):
    first_mapping = dict_to_mapping(first_sample, 'nested', text_fields=[])
    second_mapping = dict_to_mapping(second_sample, 'nested', text_fields=[])

    expected_first_mapping = {
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

    expected_second_mapping = {
        "mappings": {
            "properties": {
                "user": {
                    "type": "nested",
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
                                "city": {
                                    "type": "keyword"
                                },
                                "street": {
                                    "type": "keyword"
                                },
                                "zip_code": {
                                    "type": "keyword"
                                },
                                "geo": {
                                    "type": "nested",
                                    "properties": {
                                        "latitude": {
                                            "type": "float"
                                        },
                                        "longitude": {
                                            "type": "float"
                                        }
                                    }
                                }
                            }
                        },
                        "hobbies": {
                            "type": "keyword"
                        }
                    }
                }
            }
        }
    }

    assert second_mapping == expected_second_mapping
    assert first_mapping == expected_first_mapping

def test_dict_to_mapping_with_test_and_object(first_sample, second_sample):
    first_mapping = dict_to_mapping(first_sample, 'object', text_fields=['name'])
    second_mapping = dict_to_mapping(second_sample, 'object', text_fields=['name'])

    first_expected_mapping = {
        "mappings": {
            "properties": {
                "name": {
                    "type": "text"
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

    expected_second_mapping = {
        "mappings": {
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "text"
                        },
                        "age": {
                            "type": "integer"
                        },
                        "address": {
                            "type": "object",
                            "properties": {
                                "city": {
                                    "type": "keyword"
                                },
                                "street": {
                                    "type": "keyword"
                                },
                                "zip_code": {
                                    "type": "keyword"
                                },
                                "geo": {
                                    "type": "object",
                                    "properties": {
                                        "latitude": {
                                            "type": "float"
                                        },
                                        "longitude": {
                                            "type": "float"
                                        }
                                    }
                                }
                            }
                        },
                        "hobbies": {
                            "type": "keyword"
                        }
                    }
                }
            }
        }
    }

    assert second_mapping == expected_second_mapping
    assert first_mapping == first_expected_mapping