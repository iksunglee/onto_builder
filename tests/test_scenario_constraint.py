"""Tests for Scenario and Constraint data model classes."""

from ontobuilder.core.model import Scenario, Constraint


class TestScenario:
    def test_create_scenario(self):
        s = Scenario(
            name="reserve-room",
            description="Book a room",
            root_concept="Reservation",
            includes=["Room", "Person"],
            action="create",
        )
        assert s.name == "reserve-room"
        assert s.root_concept == "Reservation"
        assert s.includes == ["Room", "Person"]
        assert s.action == "create"

    def test_scenario_to_dict(self):
        s = Scenario(
            name="reserve-room",
            description="Book a room",
            root_concept="Reservation",
            includes=["Room", "Person"],
            action="create",
        )
        d = s.to_dict()
        assert d == {
            "name": "reserve-room",
            "description": "Book a room",
            "root_concept": "Reservation",
            "includes": ["Room", "Person"],
            "action": "create",
        }

    def test_scenario_from_dict(self):
        d = {
            "name": "check-avail",
            "description": "Check availability",
            "root_concept": "Room",
            "includes": ["Schedule"],
            "action": "read",
        }
        s = Scenario.from_dict(d)
        assert s == Scenario(**d)

    def test_scenario_roundtrip(self):
        s = Scenario(
            name="cancel",
            description="Cancel a booking",
            root_concept="Reservation",
            includes=["Reservation"],
            action="delete",
        )
        assert Scenario.from_dict(s.to_dict()) == s


class TestConstraint:
    def test_create_constraint(self):
        c = Constraint(
            name="no-double-booking",
            description="Room cannot be double booked",
            query="Reservation WHERE room = {room} AND time OVERLAPS {time}",
            violation="Room is already booked",
        )
        assert c.name == "no-double-booking"
        assert c.violation == "Room is already booked"

    def test_constraint_to_dict(self):
        c = Constraint(
            name="equip-match",
            description="Equipment must match",
            query="Room.level >= Procedure.required",
            violation="Insufficient equipment",
        )
        d = c.to_dict()
        assert d == {
            "name": "equip-match",
            "description": "Equipment must match",
            "query": "Room.level >= Procedure.required",
            "violation": "Insufficient equipment",
        }

    def test_constraint_from_dict(self):
        d = {
            "name": "auth-check",
            "description": "User must be authorized",
            "query": "User.role IN {allowed_roles}",
            "violation": "Not authorized",
        }
        c = Constraint.from_dict(d)
        assert c == Constraint(**d)

    def test_constraint_roundtrip(self):
        c = Constraint(
            name="cap",
            description="Capacity limit",
            query="Room.occupancy < Room.max_capacity",
            violation="Room full",
        )
        assert Constraint.from_dict(c.to_dict()) == c


from ontobuilder import Ontology


class TestOntologyScenarios:
    def test_add_scenario(self):
        onto = Ontology("Test")
        onto.add_concept("Room", description="A room")
        onto.add_concept("Person", description="A person")
        s = onto.add_scenario(
            "book-room",
            description="Book a room",
            root_concept="Room",
            includes=["Room", "Person"],
            action="create",
        )
        assert s.name == "book-room"
        assert "book-room" in onto.scenarios

    def test_add_constraint(self):
        onto = Ontology("Test")
        c = onto.add_constraint(
            "no-overlap",
            description="No overlapping bookings",
            query="Booking WHERE room = {room} AND time OVERLAPS {time}",
            violation="Room already booked",
        )
        assert c.name == "no-overlap"
        assert "no-overlap" in onto.constraints

    def test_scenario_serialization_roundtrip(self):
        onto = Ontology("Test", description="With scenarios")
        onto.add_concept("Room", description="A room")
        onto.add_scenario(
            "book",
            description="Book a room",
            root_concept="Room",
            includes=["Room"],
            action="create",
        )
        onto.add_constraint(
            "cap",
            description="Capacity",
            query="Room.occ < Room.max",
            violation="Full",
        )
        data = onto.to_dict()
        assert "scenarios" in data
        assert "constraints" in data
        restored = Ontology.from_dict(data)
        assert "book" in restored.scenarios
        assert "cap" in restored.constraints

    def test_empty_ontology_no_scenarios_in_dict(self):
        onto = Ontology("Test")
        data = onto.to_dict()
        assert "scenarios" not in data
        assert "constraints" not in data
