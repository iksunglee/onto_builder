"""Regression tests for first-run CLI and onboarding behavior."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ontobuilder.cli.app import app
from ontobuilder.core.ontology import Ontology
from ontobuilder.serialization.yaml_io import save_yaml


runner = CliRunner()


def _clear_llm_env(monkeypatch) -> None:
    for key in (
        "ONTOBUILDER_PROVIDER",
        "ONTOBUILDER_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "ONTOBUILDER_LLM_MODEL",
        "ONTOBUILDER_LLM_BACKEND",
        "OPENAI_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def _write_minimal_ontology(tmp_path: Path) -> None:
    onto = Ontology("First Run")
    onto.add_concept("Animal", description="A living creature")
    save_yaml(onto, tmp_path / "ontology.onto.yaml")


def test_top_level_help_uses_ascii_friendly_copy():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "OntoBuilder - A beginner-friendly ontology builder." in result.output
    assert "Configure LLM settings - choose your AI provider." in result.output
    assert "—" not in result.output


def test_infer_help_mentions_interactive_review():
    result = runner.invoke(app, ["infer", "--help"])

    assert result.exit_code == 0
    assert "interactive review" in result.output.lower()


def test_workspace_setup_prompt_mentions_offline_options(monkeypatch, tmp_path: Path):
    _clear_llm_env(monkeypatch)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["workspace"], input="n\n")

    assert result.exit_code == 1
    assert "infer --local" in result.output
    assert "basic ontology chat" in result.output.lower()


def test_chat_command_uses_clean_fallback_when_unconfigured(monkeypatch, tmp_path: Path):
    _clear_llm_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    _write_minimal_ontology(tmp_path)

    result = runner.invoke(app, ["chat", "xyzzy random gibberish"])

    assert result.exit_code == 0
    assert "Likely next actions" in result.output
    assert "ontobuilder[llm]" in result.output
    assert "AuthenticationError" not in result.output
    assert "api_key client option must be set" not in result.output


def test_readme_examples_match_current_first_run_flags():
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")

    assert "ontobuilder relation add assigned_surgeon --from SurgeryBooking --to Surgeon" in readme
    assert (
        "ontobuilder relation add assigned_surgeon --source SurgeryBooking --target Surgeon"
        not in readme
    )
    assert "offline, no API key; launches interactive review" in readme
