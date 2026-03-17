"""Tests for core data model."""

from ontobuilder.core.model import Concept, Property, Relation, Instance


def test_property_roundtrip():
    p = Property(name="age", data_type="int", required=True)
    d = p.to_dict()
    assert d == {"name": "age", "type": "int", "required": True}
    p2 = Property.from_dict(d)
    assert p2.name == "age"
    assert p2.data_type == "int"
    assert p2.required is True


def test_property_defaults():
    p = Property(name="label")
    assert p.data_type == "string"
    assert p.required is False
    d = p.to_dict()
    assert "required" not in d


def test_concept_roundtrip():
    c = Concept(
        name="Dog",
        description="A domestic animal",
        parent="Animal",
        properties=[Property("breed", "string")],
    )
    d = c.to_dict()
    assert d["name"] == "Dog"
    assert d["parent"] == "Animal"
    assert len(d["properties"]) == 1

    c2 = Concept.from_dict(d)
    assert c2.name == "Dog"
    assert c2.parent == "Animal"
    assert c2.properties[0].name == "breed"


def test_concept_minimal():
    c = Concept(name="Thing")
    d = c.to_dict()
    assert d == {"name": "Thing"}


def test_relation_roundtrip():
    r = Relation(name="sold_at", source="Animal", target="Store", cardinality="many-to-many")
    d = r.to_dict()
    assert "cardinality" not in d  # default is omitted

    r2 = Relation(name="owns", source="Person", target="Pet", cardinality="one-to-many")
    d2 = r2.to_dict()
    assert d2["cardinality"] == "one-to-many"
    r3 = Relation.from_dict(d2)
    assert r3.cardinality == "one-to-many"


def test_instance_roundtrip():
    i = Instance(name="Rex", concept="Dog", properties={"breed": "Labrador"})
    d = i.to_dict()
    assert d["properties"]["breed"] == "Labrador"
    i2 = Instance.from_dict(d)
    assert i2.concept == "Dog"
    assert i2.properties["breed"] == "Labrador"
