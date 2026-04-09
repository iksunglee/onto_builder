"""JSON Schema exporter for ontologies."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ontobuilder.core.ontology import Ontology

# Map ontobuilder property types to JSON Schema types.
_TYPE_MAP: dict[str, dict[str, str]] = {
    "string": {"type": "string"},
    "int": {"type": "integer"},
    "float": {"type": "number"},
    "bool": {"type": "boolean"},
    "date": {"type": "string", "format": "date"},
}


def _concept_schema(onto: Ontology, concept_name: str) -> dict[str, Any]:
    """Build a JSON Schema definition for a single concept."""
    concept = onto.concepts[concept_name]
    schema: dict[str, Any] = {}

    if concept.description:
        schema["description"] = concept.description

    # Collect own properties
    properties: dict[str, Any] = {}
    required: list[str] = []

    for prop in concept.properties:
        prop_schema = dict(_TYPE_MAP.get(prop.data_type, {"type": "string"}))
        properties[prop.name] = prop_schema
        if prop.required:
            required.append(prop.name)

    # Add relations where this concept is the source
    for rel in onto.relations.values():
        if rel.source == concept_name:
            ref = {"$ref": f"#/$defs/{rel.target}"}
            if rel.cardinality in ("one-to-many", "many-to-many"):
                properties[rel.name] = {"type": "array", "items": ref}
            else:
                properties[rel.name] = ref

    # Build the own-properties sub-schema
    own_schema: dict[str, Any] = {}
    if properties:
        own_schema["properties"] = properties
    if required:
        own_schema["required"] = required

    if concept.parent:
        # Use allOf to combine parent ref + own properties
        all_of: list[dict[str, Any]] = [{"$ref": f"#/$defs/{concept.parent}"}]
        if own_schema:
            all_of.append(own_schema)
        schema["allOf"] = all_of
    else:
        schema.update(own_schema)

    return schema


def export_jsonschema(onto: Ontology) -> dict[str, Any]:
    """Export ontology as a JSON Schema with ``$defs`` for each concept.

    Args:
        onto: The ontology to export.

    Returns:
        A JSON-serialisable dict representing the JSON Schema.
    """
    title = onto.name.replace(" ", "")
    schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "type": "object",
    }

    if onto.description:
        schema["description"] = onto.description

    if onto.concepts:
        defs: dict[str, Any] = {}
        for name in onto.concepts:
            defs[name] = _concept_schema(onto, name)
        schema["$defs"] = defs

    return schema


def _to_pascal(name: str) -> str:
    """Convert a kebab-case or snake_case name to PascalCase."""
    return re.sub(r"(?:^|[-_ ])\w", lambda m: m.group()[-1].upper(), name)


def _collect_concept_properties(onto: Ontology, concept_name: str) -> dict[str, Any]:
    """Collect all properties for a concept including inherited ones.

    Returns a tuple of (properties_dict, required_list).
    """
    properties: dict[str, Any] = {}
    required: list[str] = []

    # Walk up the inheritance chain to collect all properties
    chain: list[str] = []
    current = concept_name
    while current:
        chain.append(current)
        current = onto.concepts[current].parent
    # Process from root ancestor down so child properties override parent
    for cname in reversed(chain):
        concept = onto.concepts[cname]
        for prop in concept.properties:
            prop_schema = dict(_TYPE_MAP.get(prop.data_type, {"type": "string"}))
            properties[prop.name] = prop_schema
            if prop.required and prop.name not in required:
                required.append(prop.name)

    return {"properties": properties, "required": required}


def export_jsonschema_scenario(
    onto: Ontology,
    scenario_name: str,
    wrapper: str | None = None,
) -> dict[str, Any]:
    """Export a scenario-specific JSON Schema.

    Args:
        onto: The ontology to export.
        scenario_name: Name of the scenario in ``onto.scenarios``.
        wrapper: Optional wrapper format (``"openai"`` or ``"anthropic"``).

    Returns:
        A JSON-serialisable dict representing the schema or wrapped tool call.

    Raises:
        KeyError: If the scenario name is not found.
    """
    if scenario_name not in onto.scenarios:
        raise KeyError(f"Scenario '{scenario_name}' not found")

    scenario = onto.scenarios[scenario_name]
    title = _to_pascal(scenario.name)

    # Gather properties from all included concepts + root concept
    all_concepts = [scenario.root_concept] + [
        c for c in scenario.includes if c != scenario.root_concept
    ]

    properties: dict[str, Any] = {}
    required: list[str] = []

    for cname in all_concepts:
        if cname not in onto.concepts:
            continue
        collected = _collect_concept_properties(onto, cname)
        properties.update(collected["properties"])
        for r in collected["required"]:
            if r not in required:
                required.append(r)

    schema: dict[str, Any] = {
        "title": title,
        "type": "object",
        "properties": properties,
    }
    if scenario.description:
        schema["description"] = scenario.description
    if required:
        schema["required"] = required

    if wrapper == "openai":
        return {
            "type": "function",
            "function": {
                "name": title,
                "description": scenario.description,
                "parameters": schema,
            },
        }
    elif wrapper == "anthropic":
        return {
            "name": title,
            "description": scenario.description,
            "input_schema": schema,
        }

    return schema


def save_jsonschema(
    onto: Ontology,
    path: str | Path,
    *,
    scenario: str | None = None,
    wrapper: str | None = None,
) -> Path:
    """Save JSON Schema export to a file.

    Args:
        onto: The ontology to export.
        path: Destination file path.
        scenario: Optional scenario name for scenario-specific export.
        wrapper: Optional wrapper format for scenario export.

    Returns:
        The resolved Path of the written file.
    """
    path = Path(path)
    if scenario:
        data = export_jsonschema_scenario(onto, scenario, wrapper=wrapper)
    else:
        data = export_jsonschema(onto)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return path
