"""Tests for the graph backend."""

from ontobuilder.graph.networkx_backend import NetworkXBackend
from ontobuilder.core.ontology import Ontology


def test_networkx_backend_basic():
    backend = NetworkXBackend()
    backend.add_node("Animal", type="concept")
    backend.add_node("Dog", type="concept")
    backend.add_edge("Animal", "Dog", type="is_a")

    assert backend.has_node("Animal")
    assert backend.has_node("Dog")
    assert "Dog" in backend.get_children("Animal")


def test_networkx_backend_ancestors():
    backend = NetworkXBackend()
    backend.add_node("Animal")
    backend.add_node("Dog")
    backend.add_node("Poodle")
    backend.add_edge("Animal", "Dog")
    backend.add_edge("Dog", "Poodle")

    ancestors = backend.get_ancestors("Poodle")
    assert "Dog" in ancestors
    assert "Animal" in ancestors


def test_networkx_backend_remove():
    backend = NetworkXBackend()
    backend.add_node("A")
    backend.add_node("B")
    backend.add_edge("A", "B")
    backend.remove_node("B")
    assert not backend.has_node("B")
    assert backend.has_node("A")


def test_networkx_backend_roundtrip():
    backend = NetworkXBackend()
    backend.add_node("X", type="concept")
    backend.add_node("Y", type="concept")
    backend.add_edge("X", "Y", type="is_a")

    data = backend.to_dict()
    backend2 = NetworkXBackend()
    backend2.from_dict(data)
    assert backend2.has_node("X")
    assert backend2.has_node("Y")


def test_ontology_with_backend():
    onto = Ontology("Test")
    backend = NetworkXBackend()
    onto.set_backend(backend)

    onto.add_concept("Animal")
    onto.add_concept("Dog", parent="Animal")

    assert backend.has_node("Animal")
    assert backend.has_node("Dog")
    assert "Dog" in backend.get_children("Animal")


def test_ontology_set_backend_syncs_existing():
    onto = Ontology("Test")
    onto.add_concept("Animal")
    onto.add_concept("Dog", parent="Animal")
    onto.add_relation("eats", source="Animal", target="Animal")

    backend = NetworkXBackend()
    onto.set_backend(backend)

    assert backend.has_node("Animal")
    assert backend.has_node("Dog")
    assert "Dog" in backend.get_children("Animal")
