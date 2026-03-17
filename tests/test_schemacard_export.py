"""Tests for Schema Card exporter (OntoRAG-compatible format)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ontobuilder import Ontology
from ontobuilder.serialization.schemacard_io import export_schema_card, save_schema_card


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(onto: Ontology, **kwargs) -> dict:
    """Export and parse to dict in one step."""
    return json.loads(export_schema_card(onto, **kwargs))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_schemacard_valid_json(pet_store_ontology):
    """export_schema_card returns a valid JSON string."""
    raw = export_schema_card(pet_store_ontology)
    parsed = json.loads(raw)
    assert isinstance(parsed, dict)


def test_schemacard_required_keys(pet_store_ontology):
    """Output has ALL required top-level keys."""
    d = _parse(pet_store_ontology)
    required = {"version", "namespace", "classes", "datatype_properties",
                "object_properties", "events", "aliases", "warnings"}
    assert required.issubset(d.keys()), f"Missing keys: {required - d.keys()}"


def test_schemacard_class_count_matches(pet_store_ontology):
    """len(classes) equals len(onto.concepts)."""
    d = _parse(pet_store_ontology)
    assert len(d["classes"]) == len(pet_store_ontology.concepts)


def test_schemacard_empty_events_aliases(pet_store_ontology):
    """events and aliases are always empty arrays."""
    d = _parse(pet_store_ontology)
    assert d["events"] == []
    assert d["aliases"] == []


def test_schemacard_empty_ontology(empty_ontology):
    """empty_ontology → valid JSON, all arrays empty, has version and namespace."""
    d = _parse(empty_ontology)
    assert isinstance(d["version"], str) and len(d["version"]) > 0
    assert isinstance(d["namespace"], str) and len(d["namespace"]) > 0
    assert d["classes"] == []
    assert d["datatype_properties"] == []
    assert d["object_properties"] == []
    assert d["events"] == []
    assert d["aliases"] == []


def test_schemacard_warnings_for_missing_description():
    """Concept with no description generates a warning containing its name."""
    onto = Ontology("TestWarnings")
    onto.add_concept("WithDesc", description="Has a description")
    onto.add_concept("NoDesc")  # no description → should warn

    d = _parse(onto)
    warnings = d["warnings"]
    assert any("NoDesc" in w for w in warnings), (
        f"Expected warning about 'NoDesc', got: {warnings}"
    )
    # Concept with description should NOT generate a warning
    assert not any("WithDesc" in w for w in warnings), (
        f"Unexpected warning about 'WithDesc': {warnings}"
    )


def test_schemacard_class_has_required_fields(pet_store_ontology):
    """Each class entry has name, description, and origin fields."""
    d = _parse(pet_store_ontology)
    for cls in d["classes"]:
        assert "name" in cls, f"Missing 'name' in class: {cls}"
        assert "description" in cls, f"Missing 'description' in class: {cls}"
        assert "origin" in cls, f"Missing 'origin' in class: {cls}"


def test_schemacard_datatype_property_has_required_fields(pet_store_ontology):
    """Each datatype_property entry has name, domain, range, description, origin."""
    d = _parse(pet_store_ontology)
    for prop in d["datatype_properties"]:
        assert "name" in prop, f"Missing 'name' in datatype_property: {prop}"
        assert "domain" in prop, f"Missing 'domain' in datatype_property: {prop}"
        assert "range" in prop, f"Missing 'range' in datatype_property: {prop}"
        assert "description" in prop, f"Missing 'description' in datatype_property: {prop}"
        assert "origin" in prop, f"Missing 'origin' in datatype_property: {prop}"


def test_schemacard_origin_is_defined(pet_store_ontology):
    """All class and property entries have origin == 'defined'."""
    d = _parse(pet_store_ontology)
    for cls in d["classes"]:
        assert cls["origin"] == "defined", f"Expected 'defined', got {cls['origin']}"
    for prop in d["datatype_properties"]:
        assert prop["origin"] == "defined"
    for prop in d["object_properties"]:
        assert prop["origin"] == "defined"


def test_schemacard_datatype_mapping(pet_store_ontology):
    """Data types are mapped to Schema Card types (int→integer, float→number, etc.)."""
    d = _parse(pet_store_ontology)
    ranges = {p["range"] for p in d["datatype_properties"]}
    # pet_store has int, float, bool, date, string properties
    assert "integer" in ranges, f"Expected 'integer' in ranges, got: {ranges}"
    assert "number" in ranges, f"Expected 'number' in ranges, got: {ranges}"
    assert "boolean" in ranges, f"Expected 'boolean' in ranges, got: {ranges}"
    assert "date" in ranges, f"Expected 'date' in ranges, got: {ranges}"
    assert "string" in ranges, f"Expected 'string' in ranges, got: {ranges}"


def test_schemacard_object_properties(pet_store_ontology):
    """object_properties are populated from relations with domain and range."""
    d = _parse(pet_store_ontology)
    obj_props = d["object_properties"]
    assert len(obj_props) == len(pet_store_ontology.relations)
    for op in obj_props:
        assert "name" in op
        assert "domain" in op
        assert "range" in op
        assert "description" in op
        assert "origin" in op


def test_schemacard_namespace_custom(pet_store_ontology):
    """Custom namespace is used when provided."""
    custom_ns = "https://custom.example.com/ns/"
    d = _parse(pet_store_ontology, namespace=custom_ns)
    assert d["namespace"] == custom_ns


def test_schemacard_namespace_default(pet_store_ontology):
    """Default namespace is derived from ontology name."""
    d = _parse(pet_store_ontology)
    assert "Pet Store" in d["namespace"] or "PetStore" in d["namespace"] or "Pet_Store" in d["namespace"]


def test_schemacard_save_to_file(pet_store_ontology, tmp_path):
    """save_schema_card writes a valid JSON file and returns the Path."""
    out = tmp_path / "schema.json"
    result = save_schema_card(pet_store_ontology, out)
    assert result == out
    assert out.exists()
    with open(out, encoding="utf-8") as f:
        data = json.load(f)
    assert "classes" in data
    assert len(data["classes"]) == len(pet_store_ontology.concepts)


def test_schemacard_datatype_properties_flattened(pet_store_ontology):
    """datatype_properties are flattened: one entry per property per concept."""
    d = _parse(pet_store_ontology)
    # pet_store has: Animal(5 props) + Dog(1 prop) + Customer(1 prop) = 7 total
    expected_count = sum(
        len(c.properties) for c in pet_store_ontology.concepts.values()
    )
    assert len(d["datatype_properties"]) == expected_count


def test_schemacard_domain_matches_concept(pet_store_ontology):
    """Each datatype_property domain matches the concept it belongs to."""
    d = _parse(pet_store_ontology)
    # Build expected domain→props mapping
    expected: dict[str, set] = {}
    for concept in pet_store_ontology.concepts.values():
        for prop in concept.properties:
            expected.setdefault(concept.name, set()).add(prop.name)

    for dp in d["datatype_properties"]:
        domain = dp["domain"]
        name = dp["name"]
        assert domain in expected, f"Unexpected domain '{domain}'"
        assert name in expected[domain], f"Property '{name}' not in concept '{domain}'"
