"""Tests for JSON Schema export."""

import json

from ontobuilder.serialization.jsonschema_io import (
    export_jsonschema,
    export_jsonschema_scenario,
    save_jsonschema,
)


class TestJsonSchemaExport:
    def test_basic_schema(self, pet_store_ontology):
        schema = export_jsonschema(pet_store_ontology)
        assert schema["title"] == "PetStore"
        assert "$defs" in schema
        assert "Animal" in schema["$defs"]
        assert "Dog" in schema["$defs"]

    def test_property_types_mapped(self, pet_store_ontology):
        schema = export_jsonschema(pet_store_ontology)
        animal = schema["$defs"]["Animal"]
        props = animal["properties"]
        assert props["name"]["type"] == "string"
        assert props["age"]["type"] == "integer"
        assert props["weight_kg"]["type"] == "number"
        assert props["vaccinated"]["type"] == "boolean"
        assert props["birth_date"]["type"] == "string"
        assert props["birth_date"]["format"] == "date"

    def test_required_properties(self, pet_store_ontology):
        schema = export_jsonschema(pet_store_ontology)
        animal = schema["$defs"]["Animal"]
        assert "name" in animal["required"]
        assert "age" not in animal.get("required", [])

    def test_inheritance_uses_allof(self, pet_store_ontology):
        schema = export_jsonschema(pet_store_ontology)
        dog = schema["$defs"]["Dog"]
        assert "allOf" in dog
        refs = [item["$ref"] for item in dog["allOf"] if "$ref" in item]
        assert "#/$defs/Animal" in refs

    def test_concept_descriptions(self, pet_store_ontology):
        schema = export_jsonschema(pet_store_ontology)
        assert schema["$defs"]["Animal"]["description"] == "A living creature"

    def test_empty_ontology(self, empty_ontology):
        schema = export_jsonschema(empty_ontology)
        assert schema["title"] == "Empty"
        assert schema.get("$defs", {}) == {}

    def test_output_is_valid_json(self, pet_store_ontology):
        schema = export_jsonschema(pet_store_ontology)
        text = json.dumps(schema)
        parsed = json.loads(text)
        assert parsed == schema

    def test_relations_as_properties(self, pet_store_ontology):
        schema = export_jsonschema(pet_store_ontology)
        animal = schema["$defs"]["Animal"]
        # sold_at relation: Animal -> Store (many-to-many default)
        assert "sold_at" in animal["properties"]


class TestJsonSchemaScenario:
    def test_scenario_schema(self, hospital_ontology):
        schema = export_jsonschema_scenario(hospital_ontology, "reserve-operating-room")
        assert schema["title"] == "ReserveOperatingRoom"
        assert schema["description"] == "Book a surgical OR for a procedure"
        assert "properties" in schema

    def test_scenario_includes_relevant_concepts(self, hospital_ontology):
        schema = export_jsonschema_scenario(hospital_ontology, "reserve-operating-room")
        props = schema["properties"]
        assert len(props) > 0

    def test_unknown_scenario_raises(self, hospital_ontology):
        import pytest
        with pytest.raises(KeyError):
            export_jsonschema_scenario(hospital_ontology, "nonexistent")


class TestJsonSchemaOpenAIFormat:
    def test_openai_envelope(self, hospital_ontology):
        schema = export_jsonschema_scenario(
            hospital_ontology, "reserve-operating-room", wrapper="openai"
        )
        assert schema["type"] == "function"
        assert "function" in schema
        assert "parameters" in schema["function"]


class TestSaveJsonSchema:
    def test_save_to_file(self, pet_store_ontology, tmp_path):
        out = tmp_path / "schema.json"
        save_jsonschema(pet_store_ontology, out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["title"] == "PetStore"
