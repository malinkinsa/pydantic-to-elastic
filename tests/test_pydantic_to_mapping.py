from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal
from uuid import UUID

import pytest
from pydantic import BaseModel, ConfigDict, Field, RootModel

from pydantic2es.converters.pydantic2mapping import (
    UnsupportedTypeError,
    model_to_mapping,
)


class Address(BaseModel):
    city: str


class Status(str, Enum):
    ACTIVE = "active"


class User(BaseModel):
    identifier: UUID
    display_name: str = Field(alias="displayName")
    nickname: str | None = None
    address: Address
    addresses: list[Address]
    scores: set[int]
    created_at: datetime
    birthday: date
    balance: Decimal
    status: Status
    level: Literal["basic", "admin"]
    metadata: dict[str, object]


class AuditedModel(BaseModel):
    revision: int


class InheritedModel(AuditedModel):
    title: str


def test_model_to_mapping_handles_pydantic_types_and_aliases():
    properties = model_to_mapping(User)["mappings"]["properties"]

    assert properties["identifier"] == {"type": "keyword"}
    assert properties["displayName"] == {"type": "keyword"}
    assert properties["nickname"] == {"type": "keyword"}
    assert properties["address"]["type"] == "object"
    assert properties["addresses"]["type"] == "nested"
    assert properties["scores"] == {"type": "integer"}
    assert properties["created_at"] == {"type": "date", "ignore_malformed": True}
    assert properties["birthday"] == {"type": "date", "ignore_malformed": True}
    assert properties["balance"] == {"type": "double"}
    assert properties["status"] == {"type": "keyword"}
    assert properties["level"] == {"type": "keyword"}
    assert properties["metadata"] == {"type": "object"}


def test_model_to_mapping_includes_inherited_fields():
    properties = model_to_mapping(InheritedModel)["mappings"]["properties"]

    assert properties == {
        "revision": {"type": "integer"},
        "title": {"type": "keyword"},
    }


def test_model_to_mapping_supports_dotted_overrides():
    properties = model_to_mapping(
        User,
        static_fields={"text": ["address.city"], "flattened": ["metadata"]},
    )["mappings"]["properties"]

    assert properties["address"]["properties"]["city"] == {"type": "text"}
    assert properties["addresses"]["properties"]["city"] == {"type": "keyword"}
    assert properties["metadata"] == {"type": "flattened"}


def test_bare_override_applies_at_every_depth():
    properties = model_to_mapping(
        User, static_fields={"text": ["city"], "flattened": []}
    )["mappings"]["properties"]

    assert properties["address"]["properties"]["city"] == {"type": "text"}
    assert properties["addresses"]["properties"]["city"] == {"type": "text"}


def test_unknown_annotation_is_an_error_instead_of_null_mapping():
    class Opaque:
        pass

    class Model(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        value: Opaque

    with pytest.raises(UnsupportedTypeError, match="value"):
        model_to_mapping(Model)


def test_incompatible_union_is_an_error():
    class Model(BaseModel):
        value: str | int

    with pytest.raises(UnsupportedTypeError, match="union members"):
        model_to_mapping(Model)


def test_recursive_model_is_an_error():
    class Node(BaseModel):
        children: list["Node"] = []

    with pytest.raises(UnsupportedTypeError, match="recursive model"):
        model_to_mapping(Node)


def test_root_model_is_rejected_instead_of_creating_fake_root_property():
    class Tags(RootModel[list[str]]):
        pass

    with pytest.raises(UnsupportedTypeError, match="RootModel"):
        model_to_mapping(Tags)
