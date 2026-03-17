"""Core data model for ontologies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Property:
    """A property that a concept can have."""

    name: str
    data_type: str = "string"  # string, int, float, bool, date
    required: bool = False

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"name": self.name, "type": self.data_type}
        if self.required:
            d["required"] = True
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Property:
        return cls(
            name=data["name"],
            data_type=data.get("type", "string"),
            required=data.get("required", False),
        )


@dataclass
class Concept:
    """A concept (class) in the ontology."""

    name: str
    description: str = ""
    parent: str | None = None
    properties: list[Property] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"name": self.name}
        if self.description:
            d["description"] = self.description
        if self.parent:
            d["parent"] = self.parent
        if self.properties:
            d["properties"] = [p.to_dict() for p in self.properties]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Concept:
        props = [Property.from_dict(p) for p in data.get("properties", [])]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            parent=data.get("parent"),
            properties=props,
        )


@dataclass
class Relation:
    """A named relationship between two concepts."""

    name: str
    source: str
    target: str
    cardinality: str = "many-to-many"  # one-to-one, one-to-many, many-to-many

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "name": self.name,
            "source": self.source,
            "target": self.target,
        }
        if self.cardinality != "many-to-many":
            d["cardinality"] = self.cardinality
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Relation:
        return cls(
            name=data["name"],
            source=data["source"],
            target=data["target"],
            cardinality=data.get("cardinality", "many-to-many"),
        )


@dataclass
class Instance:
    """An instance (individual) of a concept."""

    name: str
    concept: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"name": self.name, "concept": self.concept}
        if self.properties:
            d["properties"] = self.properties
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Instance:
        return cls(
            name=data["name"],
            concept=data["concept"],
            properties=data.get("properties", {}),
        )
