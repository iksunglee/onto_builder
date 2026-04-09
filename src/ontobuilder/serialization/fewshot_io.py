"""Few-shot example generator from ontology instances."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ontobuilder.core.ontology import Ontology


def _instance_to_natural_language(concept_name: str, properties: dict[str, Any]) -> str:
    """Convert an instance's properties into a natural language description."""
    if not properties:
        return f"A {concept_name} with no specified properties."

    prop_parts = [f"{key} is {value}" for key, value in properties.items()]
    joined = ", ".join(prop_parts)
    return f"A {concept_name} where {joined}."


def _build_query_trace(concept_name: str, properties: dict[str, Any]) -> list[str]:
    """Build a simulated query trace for an instance."""
    trace = [f"Identify concept: {concept_name}"]
    for key, value in properties.items():
        trace.append(f"Extract property '{key}' = {value!r}")
    trace.append(f"Create {concept_name} instance")
    return trace


def export_fewshot(
    onto: Ontology,
    *,
    scenario: str | None = None,
    include_traces: bool = False,
    format: str = "examples",
) -> list[dict[str, Any]]:
    """Generate few-shot examples from ontology instances.

    Args:
        onto: The ontology to generate examples from.
        scenario: If provided, filter instances to concepts in the scenario.
        include_traces: If True, include a simulated query_trace in each example.
        format: "examples" returns structured dicts; "messages" returns
                OpenAI chat message format.

    Returns:
        A list of example dicts or message dicts.
    """
    if not onto.instances:
        return []

    # Determine which concepts to include
    allowed_concepts: set[str] | None = None
    if scenario is not None:
        sc = onto.scenarios.get(scenario)
        if sc is None:
            return []
        allowed_concepts = {sc.root_concept} | set(sc.includes)

    instances = list(onto.instances.values())
    if allowed_concepts is not None:
        instances = [i for i in instances if i.concept in allowed_concepts]

    if not instances:
        return []

    examples: list[dict[str, Any]] = []
    for inst in instances:
        input_text = _instance_to_natural_language(inst.concept, inst.properties)
        output_dict = dict(inst.properties)

        example: dict[str, Any] = {
            "input": input_text,
            "output": output_dict,
            "concept": inst.concept,
        }

        if scenario is not None:
            example["scenario"] = scenario

        if include_traces:
            example["query_trace"] = _build_query_trace(inst.concept, inst.properties)

        examples.append(example)

    if format == "messages":
        messages: list[dict[str, Any]] = []
        for ex in examples:
            messages.append({"role": "user", "content": ex["input"]})
            messages.append({"role": "assistant", "content": json.dumps(ex["output"])})
        return messages

    return examples


def save_fewshot(
    onto: Ontology,
    path: str | Path,
    **kwargs: Any,
) -> Path:
    """Export few-shot examples and save to a JSON file.

    Args:
        onto: The ontology to generate examples from.
        path: Output file path.
        **kwargs: Additional arguments passed to export_fewshot.

    Returns:
        The path to the written file.
    """
    path = Path(path)
    examples = export_fewshot(onto, **kwargs)
    path.write_text(json.dumps(examples, indent=2, default=str), encoding="utf-8")
    return path
