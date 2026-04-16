# tests/test_improve_cli.py
"""Integration tests for the improve CLI commands."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ontobuilder.cli.app import app
from ontobuilder.serialization.yaml_io import save_yaml
from ontobuilder import Ontology


runner = CliRunner()


@pytest.fixture
def onto_file(tmp_path, hospital_ontology):
    """Save hospital ontology to a temp file and chdir there."""
    path = tmp_path / "ontology.onto.yaml"
    save_yaml(hospital_ontology, path)
    return tmp_path, path


class TestAuditCLI:
    def test_audit_rich_output(self, onto_file, monkeypatch):
        tmp_path, _ = onto_file
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["improve", "audit"])
        assert result.exit_code == 0
        assert "Score" in result.output or "score" in result.output.lower()

    def test_audit_json_output(self, onto_file, monkeypatch):
        tmp_path, _ = onto_file
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["improve", "audit", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "score" in data
        assert "items" in data

    def test_audit_save_to_file(self, onto_file, monkeypatch):
        tmp_path, _ = onto_file
        monkeypatch.chdir(tmp_path)
        out = str(tmp_path / "report.json")
        result = runner.invoke(app, ["improve", "audit", "-o", out])
        assert result.exit_code == 0
        assert Path(out).exists()
        data = json.loads(Path(out).read_text(encoding="utf-8"))
        assert "score" in data

    def test_audit_no_ontology_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["improve", "audit"])
        assert result.exit_code != 0


class TestCompareCLI:
    def test_compare_rich_output(self, onto_file, monkeypatch):
        tmp_path, _ = onto_file
        monkeypatch.chdir(tmp_path)
        # Create a second ontology
        other = Ontology("Other", description="Different")
        other.add_concept("UniqueToB", description="Only in B")
        other_path = tmp_path / "other.onto.yaml"
        save_yaml(other, other_path)

        result = runner.invoke(app, ["improve", "compare", str(other_path)])
        assert result.exit_code == 0
        assert "Diff" in result.output or "Only" in result.output

    def test_compare_json_output(self, onto_file, monkeypatch):
        tmp_path, _ = onto_file
        monkeypatch.chdir(tmp_path)
        other = Ontology("Other")
        other.add_concept("NewConcept", description="New")
        other_path = tmp_path / "other.onto.yaml"
        save_yaml(other, other_path)

        result = runner.invoke(
            app, ["improve", "compare", str(other_path), "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "only_in_a" in data
        assert "only_in_b" in data

    def test_compare_merge(self, onto_file, monkeypatch):
        tmp_path, onto_path = onto_file
        monkeypatch.chdir(tmp_path)

        other = Ontology("Other")
        other.add_concept("Surgeon", description="Exists in both")
        other.add_concept("NewFromB", description="Added by merge")
        other_path = tmp_path / "other.onto.yaml"
        save_yaml(other, other_path)

        result = runner.invoke(
            app, ["improve", "compare", str(other_path), "--merge"]
        )
        assert result.exit_code == 0
        assert "Merged" in result.output

        # Verify the merged file
        from ontobuilder.serialization.yaml_io import load_yaml
        merged = load_yaml(onto_path)
        assert "Surgeon" in merged.concepts
        assert "NewFromB" in merged.concepts

    def test_compare_file_not_found(self, onto_file, monkeypatch):
        tmp_path, _ = onto_file
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["improve", "compare", "nonexistent.yaml"])
        assert result.exit_code != 0


class TestBackwardCompatibility:
    def test_existing_commands_still_work(self, onto_file, monkeypatch):
        tmp_path, _ = onto_file
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "Hospital Operations" in result.output

    def test_apply_commands_still_work(self, onto_file, monkeypatch):
        tmp_path, _ = onto_file
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["apply", "jsonschema"])
        assert result.exit_code == 0
