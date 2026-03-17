"""Tests for prompt_io — LLM system prompt text exporter."""

from __future__ import annotations

from pathlib import Path

import pytest

from ontobuilder import Ontology
from ontobuilder.serialization.prompt_io import export_prompt, save_prompt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def single_concept_ontology():
    """Ontology with one concept, no parent, no properties."""
    onto = Ontology("Simple")
    onto.add_concept("Thing")
    return onto


@pytest.fixture
def unicode_ontology():
    """Ontology with a unicode concept name."""
    onto = Ontology("Unicode Test")
    onto.add_concept("Üniversité", description="A university")
    return onto


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_prompt_full_ontology(pet_store_ontology):
    """Full ontology renders all required sections and formatting."""
    result = export_prompt(pet_store_ontology)

    # Title
    assert "# Ontology: Pet Store" in result

    # Description
    assert "A pet store domain model" in result

    # Sections
    assert "## Concepts" in result
    assert "## Relations" in result

    # Arrow in relations
    assert "→" in result

    # Required property marker
    assert "(required)" in result

    # Child concepts appear indented under parents
    lines = result.splitlines()
    animal_idx = next(i for i, l in enumerate(lines) if "- Animal:" in l)
    dog_idx = next(i for i, l in enumerate(lines) if "- Dog:" in l)
    poodle_idx = next(i for i, l in enumerate(lines) if "- Poodle:" in l)

    # Dog must come after Animal and be more indented
    assert dog_idx > animal_idx
    dog_line = lines[dog_idx]
    animal_line = lines[animal_idx]
    assert len(dog_line) - len(dog_line.lstrip()) > len(animal_line) - len(animal_line.lstrip())

    # Poodle must come after Dog and be more indented than Dog
    assert poodle_idx > dog_idx
    poodle_line = lines[poodle_idx]
    assert len(poodle_line) - len(poodle_line.lstrip()) > len(dog_line) - len(dog_line.lstrip())

    # Inheritance note
    assert "[inherits from Animal]" in result or "inherits" in result

    # Relations format: name: Source → Target (cardinality)
    assert "sold_at" in result
    assert "Animal → Store" in result


def test_prompt_empty_ontology(empty_ontology):
    """Empty ontology: title present, no section headers."""
    result = export_prompt(empty_ontology)

    assert "# Ontology: Empty" in result
    assert "## Concepts" not in result
    assert "## Relations" not in result
    assert "## Instances" not in result


def test_prompt_single_concept(single_concept_ontology):
    """Single concept with no parent or properties renders without error."""
    result = export_prompt(single_concept_ontology)

    assert "# Ontology: Simple" in result
    assert "## Concepts" in result
    assert "Thing" in result
    # No properties line expected
    assert "Properties:" not in result


def test_prompt_instances_excluded_by_default(pet_store_ontology):
    """Instances do NOT appear when include_instances=False (default)."""
    result = export_prompt(pet_store_ontology)

    assert "## Instances" not in result
    # Instance names should not appear
    assert "Rex" not in result
    assert "Fluffy" not in result


def test_prompt_instances_included(pet_store_ontology):
    """Instances appear in ## Instances section when include_instances=True."""
    result = export_prompt(pet_store_ontology, include_instances=True)

    assert "## Instances" in result
    assert "Rex" in result
    assert "Fluffy" in result
    # Format: Name (Concept)
    assert "Rex (Dog)" in result or "Rex" in result


def test_prompt_unicode(unicode_ontology):
    """Unicode concept name renders without error."""
    result = export_prompt(unicode_ontology)

    assert "# Ontology: Unicode Test" in result
    assert "Üniversité" in result


def test_prompt_save_writes_file(tmp_path, pet_store_ontology):
    """save_prompt() creates a file at the given path."""
    out = tmp_path / "prompt.txt"
    returned = save_prompt(pet_store_ontology, out)

    assert returned == out
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "# Ontology: Pet Store" in content
