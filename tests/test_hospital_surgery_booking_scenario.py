"""Tests for the hospital surgery room booking scenario fixture."""

from pathlib import Path

from ontobuilder.owl.query import StructuredQuery
from ontobuilder.owl.reasoning import OWLReasoner
from ontobuilder.serialization.yaml_io import load_yaml


def _fixture_path() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "hospital_surgery_booking.onto.yaml"


def test_hospital_surgery_booking_fixture_loads() -> None:
    onto = load_yaml(_fixture_path())

    assert onto.name == "HospitalSurgeryBooking"
    assert "SurgeryBooking" in onto.concepts
    assert "SurgeryRoom" in onto.concepts
    assert "Hospital" in onto.concepts
    assert "assigned_room" in onto.relations
    assert "scheduled_in_slot" in onto.relations

    assigned_room = onto.relations["assigned_room"]
    assert assigned_room.source == "SurgeryBooking"
    assert assigned_room.target == "SurgeryRoom"
    assert assigned_room.cardinality == "many-to-one"

    room_in_hospital = onto.relations["room_in_hospital"]
    assert room_in_hospital.source == "SurgeryRoom"
    assert room_in_hospital.target == "Hospital"
    assert room_in_hospital.cardinality == "many-to-one"


def test_hospital_surgery_booking_reasoning_and_query() -> None:
    onto = load_yaml(_fixture_path())

    reasoner = OWLReasoner(onto)
    assert reasoner.check_consistency() == []

    query = StructuredQuery(onto)
    describe = query.describe_class("SurgeryBooking")
    assert describe.count == 1

    row = describe.results[0]
    outgoing = row["outgoing_relations"]
    assert "assigned_room" in outgoing
    assert "SurgeryRoom" in outgoing
    assert "assigned_surgeon" in outgoing
    assert "Surgeon" in outgoing

    path_result = query.find_path("SurgeryBooking", "Hospital")
    assert path_result.count >= 1
    assert any(
        "assigned_room" in item["path"] and "room_in_hospital" in item["path"]
        for item in path_result.results
    )
