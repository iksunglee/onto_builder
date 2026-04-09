"""Tests for few-shot example generator."""

import json

from ontobuilder.serialization.fewshot_io import (
    export_fewshot,
    save_fewshot,
)


class TestFewShotFromInstances:
    def test_generates_examples(self, hospital_ontology):
        examples = export_fewshot(hospital_ontology)
        assert len(examples) > 0

    def test_example_structure(self, hospital_ontology):
        examples = export_fewshot(hospital_ontology)
        ex = examples[0]
        assert "input" in ex
        assert "output" in ex
        assert "concept" in ex

    def test_output_is_dict(self, hospital_ontology):
        examples = export_fewshot(hospital_ontology)
        for ex in examples:
            assert isinstance(ex["output"], dict)

    def test_input_is_natural_language(self, hospital_ontology):
        examples = export_fewshot(hospital_ontology)
        for ex in examples:
            assert isinstance(ex["input"], str)
            assert len(ex["input"]) > 10

    def test_empty_ontology_no_examples(self, empty_ontology):
        examples = export_fewshot(empty_ontology)
        assert examples == []


class TestFewShotScenario:
    def test_filter_by_scenario(self, hospital_ontology):
        examples = export_fewshot(hospital_ontology, scenario="reserve-operating-room")
        for ex in examples:
            assert ex.get("scenario") == "reserve-operating-room"

    def test_unknown_scenario_empty(self, hospital_ontology):
        examples = export_fewshot(hospital_ontology, scenario="nonexistent")
        assert examples == []


class TestFewShotWithTraces:
    def test_include_traces(self, hospital_ontology):
        examples = export_fewshot(hospital_ontology, include_traces=True)
        if examples:
            assert "query_trace" in examples[0]
            assert isinstance(examples[0]["query_trace"], list)

    def test_no_traces_by_default(self, hospital_ontology):
        examples = export_fewshot(hospital_ontology)
        for ex in examples:
            assert "query_trace" not in ex


class TestFewShotMessagesFormat:
    def test_messages_format(self, hospital_ontology):
        messages = export_fewshot(hospital_ontology, format="messages")
        assert len(messages) > 0
        for msg in messages:
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ("user", "assistant")


class TestSaveFewShot:
    def test_save_to_file(self, hospital_ontology, tmp_path):
        out = tmp_path / "fewshot.json"
        save_fewshot(hospital_ontology, out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert isinstance(data, list)
