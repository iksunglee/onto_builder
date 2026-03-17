"""Validation helpers for ontology data."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ontobuilder.core.ontology import Ontology


class ValidationError(Exception):
    """Raised when ontology data is invalid."""


def validate_concept_name_unique(onto: Ontology, name: str) -> None:
    if name in onto.concepts:
        raise ValidationError(f"Concept '{name}' already exists.")


def validate_relation_name_unique(onto: Ontology, name: str) -> None:
    if name in onto.relations:
        raise ValidationError(f"Relation '{name}' already exists.")


def validate_parent_exists(onto: Ontology, parent: str) -> None:
    if parent not in onto.concepts:
        raise ValidationError(
            f"Parent concept '{parent}' does not exist. Add it first."
        )


def validate_concept_exists(onto: Ontology, name: str) -> None:
    if name not in onto.concepts:
        raise ValidationError(f"Concept '{name}' does not exist.")


VALID_DATA_TYPES = {"string", "int", "float", "bool", "date"}


def validate_property_type(data_type: str) -> None:
    if data_type not in VALID_DATA_TYPES:
        raise ValidationError(
            f"Invalid property type '{data_type}'. Must be one of: {', '.join(sorted(VALID_DATA_TYPES))}"
        )
