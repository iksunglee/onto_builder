"""Integration tests for the full apply workflow."""

import json

import yaml

from ontobuilder import Ontology
from ontobuilder.serialization.yaml_io import save_yaml, load_yaml
from ontobuilder.serialization.jsonschema_io import export_jsonschema, export_jsonschema_scenario
from ontobuilder.serialization.prompt_enhanced import export_enhanced_prompt
from ontobuilder.serialization.fewshot_io import export_fewshot


class TestRoundtripWithScenarios:
    """Verify ontology with scenarios survives YAML roundtrip and exports correctly."""

    def test_yaml_roundtrip_preserves_scenarios(self, hospital_ontology, tmp_path):
        path = tmp_path / "hospital.onto.yaml"
        save_yaml(hospital_ontology, path)
        loaded = load_yaml(path)
        assert "reserve-operating-room" in loaded.scenarios
        assert "no-double-booking" in loaded.constraints

    def test_jsonschema_after_roundtrip(self, hospital_ontology, tmp_path):
        path = tmp_path / "hospital.onto.yaml"
        save_yaml(hospital_ontology, path)
        loaded = load_yaml(path)
        schema = export_jsonschema(loaded)
        assert "Surgeon" in schema["$defs"]

    def test_scenario_schema_after_roundtrip(self, hospital_ontology, tmp_path):
        path = tmp_path / "hospital.onto.yaml"
        save_yaml(hospital_ontology, path)
        loaded = load_yaml(path)
        schema = export_jsonschema_scenario(loaded, "reserve-operating-room")
        assert schema["title"] == "ReserveOperatingRoom"

    def test_prompt_after_roundtrip(self, hospital_ontology, tmp_path):
        path = tmp_path / "hospital.onto.yaml"
        save_yaml(hospital_ontology, path)
        loaded = load_yaml(path)
        prompt = export_enhanced_prompt(loaded, with_queries=True)
        assert "## Query Logic" in prompt
        assert "no-double-booking" in prompt

    def test_fewshot_after_roundtrip(self, hospital_ontology, tmp_path):
        path = tmp_path / "hospital.onto.yaml"
        save_yaml(hospital_ontology, path)
        loaded = load_yaml(path)
        examples = export_fewshot(loaded, scenario="reserve-operating-room")
        assert len(examples) > 0


class TestBackwardCompatibility:
    """Existing .onto.yaml files without scenarios/constraints still work."""

    def test_old_format_loads(self, tmp_path):
        old_data = {
            "ontology": {"name": "Legacy"},
            "concepts": [{"name": "Thing", "description": "A thing"}],
        }
        path = tmp_path / "legacy.onto.yaml"
        with open(path, "w") as f:
            yaml.dump(old_data, f)
        loaded = load_yaml(path)
        assert loaded.name == "Legacy"
        assert loaded.scenarios == {}
        assert loaded.constraints == {}

    def test_old_format_exports(self, tmp_path):
        old_data = {
            "ontology": {"name": "Legacy"},
            "concepts": [{"name": "Thing", "description": "A thing"}],
        }
        path = tmp_path / "legacy.onto.yaml"
        with open(path, "w") as f:
            yaml.dump(old_data, f)
        loaded = load_yaml(path)
        schema = export_jsonschema(loaded)
        assert schema["title"] == "Legacy"
        prompt = export_enhanced_prompt(loaded)
        assert "# Domain: Legacy" in prompt
