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


@pytest.fixture
def hospital_ontology():
    """A hospital operations ontology with scenarios and constraints.

    Features:
    - 5 concepts: Surgeon, OperatingRoom, Procedure, Patient, Reservation
    - Relations: performs, books, requires, assigned_to
    - Scenarios: reserve-operating-room, check-availability
    - Constraints: no-double-booking, equipment-match
    - Instances: sample surgeon, room, procedure, reservation
    """
    onto = Ontology("Hospital Operations", description="Surgical scheduling and resource allocation")

    onto.add_concept("Surgeon", description="A medical professional qualified to perform surgery")
    onto.add_concept("OperatingRoom", description="A sterile facility equipped for surgical procedures")
    onto.add_concept("Procedure", description="A surgical procedure to be performed")
    onto.add_concept("Patient", description="A person receiving medical care")
    onto.add_concept("Reservation", description="A booking of an operating room for a procedure")

    onto.add_property("Surgeon", "name", data_type="string", required=True)
    onto.add_property("Surgeon", "specialty", data_type="string")
    onto.add_property("OperatingRoom", "room_id", data_type="string", required=True)
    onto.add_property("OperatingRoom", "equipment_level", data_type="string")
    onto.add_property("Procedure", "name", data_type="string", required=True)
    onto.add_property("Procedure", "estimated_duration_min", data_type="int")
    onto.add_property("Patient", "patient_id", data_type="string", required=True)
    onto.add_property("Patient", "name", data_type="string")
    onto.add_property("Reservation", "datetime", data_type="date", required=True)
    onto.add_property("Reservation", "priority", data_type="string")

    onto.add_relation("performs", source="Surgeon", target="Procedure", cardinality="one-to-many")
    onto.add_relation("books", source="Reservation", target="OperatingRoom", cardinality="many-to-one")
    onto.add_relation("requires", source="Procedure", target="OperatingRoom", cardinality="many-to-one")
    onto.add_relation("assigned_to", source="Reservation", target="Patient", cardinality="many-to-one")

    onto.add_scenario(
        "reserve-operating-room",
        description="Book a surgical OR for a procedure",
        root_concept="Reservation",
        includes=["Surgeon", "OperatingRoom", "Procedure", "Patient"],
        action="create",
    )
    onto.add_scenario(
        "check-availability",
        description="Check if an operating room is available",
        root_concept="OperatingRoom",
        includes=["Reservation"],
        action="read",
    )

    onto.add_constraint(
        "no-double-booking",
        description="An OperatingRoom cannot have overlapping Reservations",
        query="Reservation WHERE operating_room = {room} AND datetime OVERLAPS {time}",
        violation="Room is already booked at this time",
    )
    onto.add_constraint(
        "equipment-match",
        description="Room equipment must meet procedure requirements",
        query="OperatingRoom.equipment_level >= Procedure.required_equipment",
        violation="Room equipment insufficient for this procedure",
    )

    onto.add_instance("Dr. Smith", concept="Surgeon", properties={"name": "Dr. Smith", "specialty": "Orthopedics"})
    onto.add_instance("Dr. Kim", concept="Surgeon", properties={"name": "Dr. Kim", "specialty": "General Surgery"})
    onto.add_instance("OR-1", concept="OperatingRoom", properties={"room_id": "OR-1", "equipment_level": "advanced"})
    onto.add_instance("OR-2", concept="OperatingRoom", properties={"room_id": "OR-2", "equipment_level": "basic"})
    onto.add_instance("Knee Replacement", concept="Procedure", properties={"name": "Knee Replacement", "estimated_duration_min": 120})
    onto.add_instance("Appendectomy", concept="Procedure", properties={"name": "Appendectomy", "estimated_duration_min": 60})
    onto.add_instance("P-1001", concept="Patient", properties={"patient_id": "P-1001", "name": "Jane Doe"})

    return onto
