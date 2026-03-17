"""Tests for the Ontology class."""

import pytest
from ontobuilder.core.ontology import Ontology
from ontobuilder.core.validation import ValidationError


def test_create_ontology():
    onto = Ontology("Test")
    assert onto.name == "Test"
    assert len(onto.concepts) == 0


def test_add_concept():
    onto = Ontology("Test")
    c = onto.add_concept("Animal", description="A living creature")
    assert c.name == "Animal"
    assert "Animal" in onto.concepts


def test_add_concept_with_parent():
    onto = Ontology("Test")
    onto.add_concept("Animal")
    onto.add_concept("Dog", parent="Animal")
    assert onto.concepts["Dog"].parent == "Animal"


def test_add_concept_duplicate():
    onto = Ontology("Test")
    onto.add_concept("Animal")
    with pytest.raises(ValidationError, match="already exists"):
        onto.add_concept("Animal")


def test_add_concept_missing_parent():
    onto = Ontology("Test")
    with pytest.raises(ValidationError, match="does not exist"):
        onto.add_concept("Dog", parent="Animal")


def test_remove_concept():
    onto = Ontology("Test")
    onto.add_concept("Animal")
    onto.add_concept("Dog", parent="Animal")
    onto.add_relation("eats", source="Animal", target="Animal")
    onto.remove_concept("Animal")
    assert "Animal" not in onto.concepts
    assert onto.concepts["Dog"].parent is None
    assert "eats" not in onto.relations


def test_add_property():
    onto = Ontology("Test")
    onto.add_concept("Animal")
    p = onto.add_property("Animal", "species", data_type="string", required=True)
    assert p.name == "species"
    assert onto.concepts["Animal"].properties[0].data_type == "string"


def test_add_property_invalid_type():
    onto = Ontology("Test")
    onto.add_concept("Animal")
    with pytest.raises(ValidationError, match="Invalid property type"):
        onto.add_property("Animal", "x", data_type="list")


def test_add_property_duplicate():
    onto = Ontology("Test")
    onto.add_concept("Animal")
    onto.add_property("Animal", "species")
    with pytest.raises(ValidationError, match="already exists"):
        onto.add_property("Animal", "species")


def test_add_relation():
    onto = Ontology("Test")
    onto.add_concept("Animal")
    onto.add_concept("Store")
    r = onto.add_relation("sold_at", source="Animal", target="Store")
    assert r.source == "Animal"
    assert "sold_at" in onto.relations


def test_add_relation_missing_concept():
    onto = Ontology("Test")
    onto.add_concept("Animal")
    with pytest.raises(ValidationError):
        onto.add_relation("sold_at", source="Animal", target="Store")


def test_remove_relation():
    onto = Ontology("Test")
    onto.add_concept("A")
    onto.add_concept("B")
    onto.add_relation("r", source="A", target="B")
    onto.remove_relation("r")
    assert "r" not in onto.relations


def test_add_instance():
    onto = Ontology("Test")
    onto.add_concept("Dog")
    i = onto.add_instance("Rex", concept="Dog", properties={"breed": "Lab"})
    assert i.concept == "Dog"
    assert onto.instances["Rex"].properties["breed"] == "Lab"


def test_print_tree():
    onto = Ontology("Zoo")
    onto.add_concept("Animal")
    onto.add_concept("Dog", parent="Animal")
    onto.add_concept("Cat", parent="Animal")
    onto.add_concept("Poodle", parent="Dog")
    tree = onto.print_tree()
    assert "Animal" in tree
    assert "Dog" in tree
    assert "Poodle" in tree


def test_to_dict_from_dict_roundtrip():
    onto = Ontology("Shop", description="A pet shop")
    onto.add_concept("Animal", description="Living thing")
    onto.add_concept("Dog", parent="Animal")
    onto.add_property("Dog", "breed")
    onto.add_relation("sold_at", source="Animal", target="Animal")
    onto.add_instance("Rex", concept="Dog", properties={"breed": "Lab"})

    d = onto.to_dict()
    onto2 = Ontology.from_dict(d)
    assert onto2.name == "Shop"
    assert "Dog" in onto2.concepts
    assert onto2.concepts["Dog"].parent == "Animal"
    assert len(onto2.relations) == 1
    assert len(onto2.instances) == 1


def test_repr():
    onto = Ontology("Test")
    assert "Test" in repr(onto)
