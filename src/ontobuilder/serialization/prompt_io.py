"""LLM system prompt text exporter for ontologies."""

from __future__ import annotations

from pathlib import Path

from ontobuilder.core.ontology import Ontology


def export_prompt(
    onto: Ontology,
    include_instances: bool = False,
    max_concepts: int | None = None,
) -> str:
    """Export ontology as LLM system prompt text.

    Args:
        onto: The ontology to export.
        include_instances: Whether to include an ## Instances section.
        max_concepts: If set, limit the number of concepts rendered.

    Returns:
        A structured text string suitable for use as an LLM system prompt.
    """
    lines: list[str] = []

    # --- Title ---
    lines.append(f"# Ontology: {onto.name}")
    if onto.description:
        lines.append(onto.description)

    # --- Concepts section ---
    if onto.concepts:
        lines.append("")
        lines.append("## Concepts")

        # Build children map: parent_name -> [child_name, ...]
        children: dict[str | None, list[str]] = {}
        for concept in onto.concepts.values():
            parent = concept.parent
            children.setdefault(parent, []).append(concept.name)

        # Sort children lists for deterministic output
        for key in children:
            children[key].sort()

        rendered_count = 0

        def render_concept(name: str, depth: int) -> None:
            nonlocal rendered_count
            if max_concepts is not None and rendered_count >= max_concepts:
                return
            concept = onto.concepts[name]
            indent = "  " * depth
            label = f"- {concept.name}"
            if concept.description:
                label += f": {concept.description}"
            if concept.parent:
                label += f" [inherits from {concept.parent}]"
            lines.append(f"{indent}{label}")
            rendered_count += 1

            # Properties line
            if concept.properties:
                prop_parts = []
                for prop in concept.properties:
                    if prop.required:
                        part = f"{prop.name} ({prop.data_type}) (required)"
                    else:
                        part = f"{prop.name} ({prop.data_type})"
                    prop_parts.append(part)
                lines.append(f"{indent}  Properties: {', '.join(prop_parts)}")

            # Recurse into children
            for child_name in children.get(name, []):
                render_concept(child_name, depth + 1)

        # Render root concepts (parent=None) sorted
        for root_name in sorted(children.get(None, [])):
            render_concept(root_name, 0)

    # --- Relations section ---
    if onto.relations:
        lines.append("")
        lines.append("## Relations")
        for rel in onto.relations.values():
            lines.append(
                f"- {rel.name}: {rel.source} → {rel.target} ({rel.cardinality})"
            )

    # --- Instances section ---
    if include_instances and onto.instances:
        lines.append("")
        lines.append("## Instances")
        for inst in onto.instances.values():
            props_str = ""
            if inst.properties:
                props_str = ", ".join(
                    f"{k}={v}" for k, v in inst.properties.items()
                )
                props_str = f": {props_str}"
            lines.append(f"- {inst.name} ({inst.concept}){props_str}")

    return "\n".join(lines)


def save_prompt(onto: Ontology, path: str | Path, **kwargs) -> Path:
    """Save prompt export to file.

    Args:
        onto: The ontology to export.
        path: Destination file path.
        **kwargs: Additional keyword arguments forwarded to export_prompt.

    Returns:
        The resolved Path of the written file.
    """
    path = Path(path)
    content = export_prompt(onto, **kwargs)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
