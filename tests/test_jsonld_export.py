"""Tests for JSON-LD export functionality."""

from __future__ import annotations

import json

import pytest

from ontobuilder import Ontology
from ontobuilder.serialization.jsonld_io import export_jsonld, save_jsonld


def test_jsonld_valid_json(pet_store_ontology):
    """pet_store_ontology → json.loads() succeeds."""
    result = export_jsonld(pet_store_ontology)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_jsonld_has_context(pet_store_ontology):
    """Output has @context key with @vocab, owl, rdfs, xsd sub-keys."""
    result = export_jsonld(pet_store_ontology)
    parsed = json.loads(result)
    assert "@context" in parsed
    ctx = parsed["@context"]
    assert "@vocab" in ctx
    assert "owl" in ctx
    assert "rdfs" in ctx
    assert "xsd" in ctx


def test_jsonld_classes_have_id_and_type(pet_store_ontology):
    """Every node with @type == 'owl:Class' in @graph has @id."""
    result = export_jsonld(pet_store_ontology)
    parsed = json.loads(result)
    assert "@graph" in parsed
    for node in parsed["@graph"]:
        if node.get("@type") == "owl:Class":
            assert "@id" in node, f"owl:Class node missing @id: {node}"


def test_jsonld_parent_becomes_subclassof(pet_store_ontology):
    """Dog has rdfs:subClassOf pointing to Animal's @id."""
    result = export_jsonld(pet_store_ontology)
    parsed = json.loads(result)
    graph = parsed["@graph"]

    # Find Dog node
    dog_node = next((n for n in graph if n.get("rdfs:label") == "Dog"), None)
    assert dog_node is not None, "Dog node not found in @graph"
    assert "rdfs:subClassOf" in dog_node, "Dog missing rdfs:subClassOf"

    # Find Animal node
    animal_node = next((n for n in graph if n.get("rdfs:label") == "Animal"), None)
    assert animal_node is not None, "Animal node not found in @graph"

    # Dog's subClassOf should reference Animal's @id
    sub_class_of = dog_node["rdfs:subClassOf"]
    assert sub_class_of["@id"] == animal_node["@id"]


def test_jsonld_empty_ontology(empty_ontology):
    """empty_ontology → valid JSON, @graph is empty list."""
    result = export_jsonld(empty_ontology)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)
    assert "@graph" in parsed
    assert parsed["@graph"] == []


def test_jsonld_custom_namespace(pet_store_ontology):
    """namespace='http://example.com/test/' → @vocab uses provided namespace."""
    custom_ns = "http://example.com/test/"
    result = export_jsonld(pet_store_ontology, namespace=custom_ns)
    parsed = json.loads(result)
    assert parsed["@context"]["@vocab"] == custom_ns


def test_jsonld_default_namespace(pet_store_ontology):
    """No namespace arg → @vocab contains 'ontologies'."""
    result = export_jsonld(pet_store_ontology)
    parsed = json.loads(result)
    assert "ontologies" in parsed["@context"]["@vocab"]


def test_jsonld_uri_safe_ids(pet_store_ontology):
    """Concept name 'My Store' → @id contains 'my_store' (URI-safe)."""
    onto = Ontology("My Store", description="Test")
    onto.add_concept("My Store", description="A store")
    result = export_jsonld(onto)
    parsed = json.loads(result)
    graph = parsed["@graph"]
    # Find the concept node
    class_node = next((n for n in graph if n.get("@type") == "owl:Class"), None)
    assert class_node is not None
    assert "my_store" in class_node["@id"]


def test_jsonld_properties_have_xsd_range(pet_store_ontology):
    """Properties include XSD-typed rdfs:range."""
    result = export_jsonld(pet_store_ontology)
    parsed = json.loads(result)
    graph = parsed["@graph"]

    # Find DatatypeProperty nodes
    datatype_props = [n for n in graph if n.get("@type") == "owl:DatatypeProperty"]
    assert len(datatype_props) > 0, "No DatatypeProperty nodes found"

    for prop_node in datatype_props:
        assert "rdfs:range" in prop_node, f"DatatypeProperty missing rdfs:range: {prop_node}"
        range_val = prop_node["rdfs:range"]
        assert "@id" in range_val, f"rdfs:range missing @id: {range_val}"
        assert range_val["@id"].startswith("xsd:"), f"rdfs:range not XSD type: {range_val}"


def test_jsonld_relations_as_object_properties(pet_store_ontology):
    """Relations appear as owl:ObjectProperty nodes in @graph."""
    result = export_jsonld(pet_store_ontology)
    parsed = json.loads(result)
    graph = parsed["@graph"]

    obj_props = [n for n in graph if n.get("@type") == "owl:ObjectProperty"]
    assert len(obj_props) > 0, "No ObjectProperty nodes found"

    for prop_node in obj_props:
        assert "@id" in prop_node
        assert "rdfs:domain" in prop_node
        assert "rdfs:range" in prop_node


def test_jsonld_save_to_file(tmp_path, pet_store_ontology):
    """save_jsonld writes valid JSON-LD to file."""
    out_path = tmp_path / "test.jsonld"
    returned_path = save_jsonld(pet_store_ontology, out_path)
    assert returned_path == out_path
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    parsed = json.loads(content)
    assert "@context" in parsed
    assert "@graph" in parsed
