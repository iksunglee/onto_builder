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


@dataclass
class Scenario:
    """A usage scenario describing how concepts are used together."""

    name: str
    description: str
    root_concept: str
    includes: list[str] = field(default_factory=list)
    action: str = "create"  # create, read, update, delete

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "root_concept": self.root_concept,
            "includes": self.includes,
            "action": self.action,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Scenario:
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            root_concept=data["root_concept"],
            includes=data.get("includes", []),
            action=data.get("action", "create"),
        )


@dataclass
class Constraint:
    """A constraint rule that must hold in the ontology."""

    name: str
    description: str
    query: str
    violation: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "query": self.query,
            "violation": self.violation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Constraint:
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            query=data.get("query", ""),
            violation=data.get("violation", ""),
        )
