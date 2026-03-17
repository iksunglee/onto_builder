"""Pytest fixtures for ontobuilder test suite."""

import pytest
from ontobuilder import Ontology


@pytest.fixture
def pet_store_ontology():
    """A pet store domain ontology with comprehensive test data.
    
    Features:
    - 5 concepts with parent-child hierarchy (Animal → Dog → Poodle)
    - All 5 data types: string, int, float, bool, date
    - Required properties
    - Self-referencing relation (eats: Animal → Animal)
    - Multiple instances with mixed property types
    """
    onto = Ontology("Pet Store", description="A pet store domain model")
    
    # Add concepts (parents first to satisfy validation)
    onto.add_concept("Animal", description="A living creature")
    onto.add_concept("Dog", parent="Animal", description="A domestic dog")
    onto.add_concept("Poodle", parent="Dog", description="A poodle breed")
    onto.add_concept("Store", description="A retail store")
    onto.add_concept("Customer", description="A person who buys pets")
    
    # Add properties with ALL 5 data types
    onto.add_property("Animal", "name", data_type="string", required=True)
    onto.add_property("Animal", "age", data_type="int")
    onto.add_property("Animal", "weight_kg", data_type="float")
    onto.add_property("Animal", "vaccinated", data_type="bool")
    onto.add_property("Animal", "birth_date", data_type="date")
    onto.add_property("Dog", "breed", data_type="string")
    onto.add_property("Customer", "name", data_type="string", required=True)
    
    # Add relations (3+ including self-referencing)
    onto.add_relation("sold_at", source="Animal", target="Store")
    onto.add_relation("buys", source="Customer", target="Animal")
    onto.add_relation("eats", source="Animal", target="Animal")  # self-referencing
    
    # Add instances with mixed property types
    onto.add_instance(
        "Rex",
        concept="Dog",
        properties={
            "name": "Rex",
            "breed": "Labrador",
            "age": 3,
            "weight_kg": 32.5,
            "vaccinated": True,
        },
    )
    onto.add_instance(
        "Fluffy",
        concept="Poodle",
        properties={
            "name": "Fluffy",
            "breed": "Standard Poodle",
            "age": 2,
            "weight_kg": 28.0,
            "vaccinated": False,
        },
    )
    onto.add_instance(
        "FurryPaws",
        concept="Store",
        properties={"name": "Furry Paws"},
    )
    
    return onto


@pytest.fixture
def empty_ontology():
    """An empty ontology with no concepts, relations, or instances."""
    return Ontology("Empty")
