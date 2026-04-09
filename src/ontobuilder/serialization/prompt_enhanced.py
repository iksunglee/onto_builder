"""Enhanced LLM system prompt builder for ontologies."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from ontobuilder.core.ontology import Ontology


_ALL_SECTIONS = ["overview", "concepts", "rules", "constraints", "values", "scenarios"]


def _build_overview(onto: Ontology) -> list[str]:
    """Section 1: domain name and description."""
    lines = [f"# Domain: {onto.name}"]
    if onto.description:
        lines.append(onto.description)
    return lines


def _build_concepts(onto: Ontology) -> list[str]:
    """Section 2: core concepts with properties."""
    if not onto.concepts:
        return []
    lines = ["## Core Concepts"]

    children: dict[str | None, list[str]] = defaultdict(list)
    for concept in onto.concepts.values():
        children[concept.parent].append(concept.name)
    for key in children:
        children[key].sort()

    def _render(name: str, depth: int) -> None:
        concept = onto.concepts[name]
        indent = "  " * depth
        label = f"- **{concept.name}**"
        if concept.description:
            label += f": {concept.description}"
        if concept.parent:
            label += f" [inherits {concept.parent}]"
        lines.append(f"{indent}{label}")

        if concept.properties:
            for prop in concept.properties:
                req = " **(required)**" if prop.required else ""
                lines.append(f"{indent}  - `{prop.name}` ({prop.data_type}){req}")

        for child_name in children.get(name, []):
            _render(child_name, depth + 1)

    for root in children.get(None, []):
        _render(root, 0)

    return lines


def _build_rules(onto: Ontology) -> list[str]:
    """Section 3: relationships and cardinalities."""
    if not onto.relations:
        return []
    lines = ["## Relationships & Rules"]
    for rel in onto.relations.values():
        lines.append(
            f"- **{rel.name}**: {rel.source} -> {rel.target} ({rel.cardinality})"
        )
    return lines


def _build_constraints(onto: Ontology) -> list[str]:
    """Section 4: user-defined constraints + inferred required-property constraints."""
    explicit = list(onto.constraints.values()) if onto.constraints else []

    inferred: list[dict[str, str]] = []
    for concept in onto.concepts.values():
        for prop in concept.properties:
            if prop.required:
                inferred.append(
                    {
                        "name": f"{concept.name}.{prop.name}-required",
                        "description": f"{concept.name}.{prop.name} is required",
                    }
                )

    if not explicit and not inferred:
        return []

    lines = ["## Constraints"]

    for c in explicit:
        lines.append(f"- **{c.name}**: {c.description}")
        if c.violation:
            lines.append(f"  - Violation: {c.violation}")

    if inferred:
        lines.append("")
        lines.append("**Inferred from required properties:**")
        for item in inferred:
            lines.append(f"- {item['description']}")

    return lines


def _build_values(onto: Ontology) -> list[str]:
    """Section 5: valid values extracted from instances.

    Only properties with 2+ unique string values are listed.
    """
    if not onto.instances:
        return []

    prop_values: dict[str, set[str]] = defaultdict(set)
    for inst in onto.instances.values():
        for key, val in inst.properties.items():
            if isinstance(val, str):
                prop_values[key].add(val)

    # Keep only properties with 2+ unique values
    valid = {k: sorted(v) for k, v in prop_values.items() if len(v) >= 2}
    if not valid:
        return []

    lines = ["## Valid Values"]
    for prop_name, vals in sorted(valid.items()):
        lines.append(f"- **{prop_name}**: {', '.join(vals)}")
    return lines


def _build_scenarios(onto: Ontology) -> list[str]:
    """Section 6: available scenarios."""
    if not onto.scenarios:
        return []
    lines = ["## Available Scenarios"]
    for sc in onto.scenarios.values():
        lines.append(f"- **{sc.name}** ({sc.action}): {sc.description}")
        if sc.includes:
            lines.append(f"  - Involves: {', '.join(sc.includes)}")
    return lines


def _build_query_logic() -> list[str]:
    """Optional: query logic steps."""
    return [
        "## Query Logic",
        "",
        "When processing a request, follow these steps:",
        "",
        "1. **Identify Intent** - Determine the action (create, read, update, delete)",
        "2. **Resolve Entities** - Map user references to known concepts and instances",
        "3. **Validate Constraints** - Check all constraints before executing",
        "4. **Execute Action** - Perform the requested operation",
        "5. **Report** - Return a structured result with status and details",
    ]


def _build_developer_notes() -> list[str]:
    """Optional: technical notes for developer audience."""
    return [
        "## Technical Notes",
        "",
        "- Entities conform to their concept's JSON Schema definitions",
        "- Required properties must be present on create/update operations",
        "- Constraint violations should return structured error responses",
    ]


_SECTION_BUILDERS: dict[str, Any] = {
    "overview": _build_overview,
    "concepts": _build_concepts,
    "rules": _build_rules,
    "constraints": _build_constraints,
    "values": _build_values,
    "scenarios": _build_scenarios,
}


def export_enhanced_prompt(
    onto: Ontology,
    *,
    sections: list[str] | None = None,
    with_queries: bool = False,
    audience: str = "developer",
    max_tokens: int | None = None,
) -> str:
    """Build a structured system prompt from ontology data.

    Args:
        onto: The ontology to export.
        sections: Which sections to include (None = all).
        with_queries: Whether to append a Query Logic section.
        audience: ``"developer"`` adds technical notes; ``"enduser"`` omits them.
        max_tokens: If set, truncate the output to roughly this many tokens
                    (estimated as chars / 4).

    Returns:
        A markdown-formatted system prompt string.
    """
    active = sections if sections is not None else list(_ALL_SECTIONS)
    parts: list[str] = []

    for section_name in active:
        builder = _SECTION_BUILDERS.get(section_name)
        if builder is None:
            continue
        section_lines = builder(onto)
        if section_lines:
            parts.append("\n".join(section_lines))

    if with_queries:
        parts.append("\n".join(_build_query_logic()))

    if audience == "developer":
        parts.append("\n".join(_build_developer_notes()))

    result = "\n\n".join(parts)

    if max_tokens is not None:
        char_limit = max_tokens * 4
        if len(result) > char_limit:
            result = result[:char_limit].rstrip() + "\n\n[truncated]"

    return result


def save_enhanced_prompt(
    onto: Ontology, path: str | Path, **kwargs: Any
) -> Path:
    """Save enhanced prompt export to file.

    Args:
        onto: The ontology to export.
        path: Destination file path.
        **kwargs: Additional keyword arguments forwarded to export_enhanced_prompt.

    Returns:
        The resolved Path of the written file.
    """
    path = Path(path)
    content = export_enhanced_prompt(onto, **kwargs)
    path.write_text(content, encoding="utf-8")
    return path
