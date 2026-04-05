"""Infer ontology structure from data — via LLM or local heuristics."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import TYPE_CHECKING

from ontobuilder.core.ontology import Ontology
from ontobuilder.core.validation import VALID_DATA_TYPES

if TYPE_CHECKING:
    from ontobuilder.llm.schemas import OntologySuggestion


def read_sample_data(file_path: str | Path, max_rows: int = 20) -> str:
    """Read first N rows of a data file and return as formatted string."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return _read_csv(path, max_rows)
    elif suffix == ".json":
        return _read_json(path, max_rows)
    else:
        return _read_text(path, max_rows)


def _read_csv(path: Path, max_rows: int) -> str:
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = []
        for i, row in enumerate(reader):
            if i >= max_rows + 1:  # +1 for header
                break
            rows.append(row)

    if not rows:
        return "(empty file)"

    # Format as markdown table
    header = rows[0]
    lines = [" | ".join(header), " | ".join("---" for _ in header)]
    for row in rows[1:]:
        lines.append(" | ".join(row))
    return "\n".join(lines)


def _read_json(path: Path, max_rows: int) -> str:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        sample = data[:max_rows]
    else:
        sample = data

    return json.dumps(sample, indent=2, default=str)[:3000]


def _read_text(path: Path, max_rows: int) -> str:
    with open(path, "r", encoding="utf-8") as f:
        lines = []
        for i, line in enumerate(f):
            if i >= max_rows:
                break
            lines.append(line.rstrip())
    return "\n".join(lines)


def _normalize_data_type(data_type: str) -> str:
    return data_type if data_type in VALID_DATA_TYPES else "string"


def build_ontology_from_suggestion(suggestion: OntologySuggestion) -> Ontology:
    """Build an Ontology from an LLM suggestion."""
    onto = Ontology(suggestion.name, description=suggestion.description)

    added: set[str] = set()
    remaining = list(suggestion.concepts)
    max_passes = len(remaining) + 1
    while remaining and max_passes > 0:
        max_passes -= 1
        still_remaining = []
        for concept in remaining:
            if concept.parent and concept.parent not in added:
                still_remaining.append(concept)
                continue

            parent = concept.parent if concept.parent and concept.parent in added else None
            onto.add_concept(concept.name, description=concept.description, parent=parent)
            for prop in concept.properties:
                onto.add_property(
                    concept.name,
                    prop.name,
                    data_type=_normalize_data_type(prop.data_type),
                    required=prop.required,
                )
            added.add(concept.name)
        remaining = still_remaining

    for relation in suggestion.relations:
        if relation.source in added and relation.target in added:
            onto.add_relation(
                relation.name,
                source=relation.source,
                target=relation.target,
                cardinality=relation.cardinality,
            )

    return onto


def infer_ontology(file_path: str | Path, *, local: bool = False) -> Ontology | None:
    """Infer an ontology from a data file.

    Args:
        file_path: Path to CSV, JSON, or text file.
        local: If True, use local heuristic analysis (no LLM needed).
               If False, use LLM for richer inference.

    Returns the built Ontology, or None if cancelled.
    """
    path = Path(file_path)
    if not path.exists():
        from rich import print as rprint

        rprint(f"[red]File not found: {path}[/red]")
        return None

    if local:
        return _infer_local(path)
    return _infer_llm(path)


def _infer_local(path: Path) -> Ontology | None:
    """Infer ontology using local heuristic analysis — no LLM required.

    Delegates to InteractiveBuilder which lets users review and edit
    every concept, property, and relation before building.
    """
    from ontobuilder.tool.interactive import InteractiveBuilder

    builder = InteractiveBuilder()
    return builder.run(str(path))


def _infer_llm(path: Path) -> Ontology | None:
    """Infer ontology using LLM — with per-node review and edit loop."""
    from rich import print as rprint
    from rich.prompt import Confirm, Prompt

    from ontobuilder.llm.client import chat
    from ontobuilder.llm.schemas import OntologySuggestion
    from ontobuilder.llm.prompts import infer_prompt

    rprint(f"\n[bold]Analyzing data with AI: {path.name}[/bold]\n")

    sample = read_sample_data(path)
    rprint("[dim]Sample data:[/dim]")
    for line in sample.split("\n")[:10]:
        rprint(f"  {line}")
    if sample.count("\n") > 10:
        rprint(f"  ... ({sample.count(chr(10)) - 10} more lines)")

    rprint("\n[bold]Inferring ontology structure...[/bold]\n")

    suggestion: OntologySuggestion = chat(
        infer_prompt(sample),
        response_model=OntologySuggestion,
    )

    rprint(f"[bold]Suggested ontology: {suggestion.name}[/bold]")
    if suggestion.description:
        rprint(f"  {suggestion.description}")

    # Step 1: Review concepts one by one
    rprint("\n[bold]Review concepts:[/bold]")
    confirmed_concepts = []
    for c in suggestion.concepts:
        parent = f" (child of {c.parent})" if c.parent else ""
        props = ", ".join(f"{p.name}:{p.data_type}" for p in c.properties)
        rprint(f"\n  [bold]{c.name}[/bold]{parent}")
        if c.description:
            rprint(f"  {c.description}")
        if props:
            rprint(f"  Properties: {props}")

        if Confirm.ask("  Include?", default=True):
            new_name = Prompt.ask("  Name", default=c.name)
            c.name = new_name
            confirmed_concepts.append(c)

    if not confirmed_concepts:
        rprint("[yellow]No concepts accepted. Aborting.[/yellow]")
        return None

    # Step 2: Review relations
    confirmed_names = {c.name for c in confirmed_concepts}
    valid_relations = [
        r for r in suggestion.relations
        if r.source in confirmed_names and r.target in confirmed_names
    ]

    confirmed_relations = []
    if valid_relations:
        rprint("\n[bold]Review relations:[/bold]")
        for r in valid_relations:
            rprint(f"\n  [bold]{r.source}[/bold] --[{r.name}]--> [bold]{r.target}[/bold]")
            if Confirm.ask("  Include?", default=True):
                new_name = Prompt.ask("  Name", default=r.name)
                r.name = new_name
                confirmed_relations.append(r)

    # Build with confirmed items
    suggestion.concepts = confirmed_concepts
    suggestion.relations = confirmed_relations
    onto = build_ontology_from_suggestion(suggestion)

    # Step 3: Edit loop
    rprint("\n[bold green]Ontology built![/bold green]\n")
    rprint(onto.print_tree())
    onto = _edit_loop(onto)

    return onto


def _edit_loop(onto: Ontology) -> Ontology:
    """Let users add/remove concepts, properties, relations after initial build."""
    from rich import print as rprint
    from rich.prompt import Prompt

    rprint(
        "\n[dim]Commands: add-concept, add-property, add-relation, "
        "remove-concept, remove-relation, tree, done[/dim]"
    )

    while True:
        try:
            cmd = Prompt.ask("\n  Edit", default="done")
        except (EOFError, KeyboardInterrupt):
            break

        if cmd == "done":
            break
        elif cmd == "tree":
            rprint(f"\n{onto.print_tree()}")
        elif cmd == "add-concept":
            name = Prompt.ask("  Concept name")
            desc = Prompt.ask("  Description", default="")
            parent_choices = ["(none)"] + list(onto.concepts.keys())
            parent = Prompt.ask("  Parent", choices=parent_choices, default="(none)")
            try:
                onto.add_concept(
                    name, description=desc,
                    parent=parent if parent != "(none)" else None,
                )
                rprint(f"  [green]Added: {name}[/green]")
            except Exception as e:
                rprint(f"  [red]{e}[/red]")
        elif cmd == "add-property":
            concepts = list(onto.concepts.keys())
            if not concepts:
                rprint("  [yellow]No concepts yet.[/yellow]")
                continue
            concept = Prompt.ask("  On concept", choices=concepts)
            name = Prompt.ask("  Property name")
            dtype = Prompt.ask(
                "  Type",
                choices=["string", "int", "float", "bool", "date"],
                default="string",
            )
            try:
                onto.add_property(concept, name, data_type=dtype)
                rprint(f"  [green]Added: {name} ({dtype}) on {concept}[/green]")
            except Exception as e:
                rprint(f"  [red]{e}[/red]")
        elif cmd == "add-relation":
            concepts = list(onto.concepts.keys())
            if len(concepts) < 2:
                rprint("  [yellow]Need at least 2 concepts.[/yellow]")
                continue
            name = Prompt.ask("  Relation name")
            source = Prompt.ask("  Source", choices=concepts)
            target = Prompt.ask("  Target", choices=concepts)
            card = Prompt.ask(
                "  Cardinality",
                choices=["one-to-one", "one-to-many", "many-to-one", "many-to-many"],
                default="many-to-one",
            )
            try:
                onto.add_relation(name, source=source, target=target, cardinality=card)
                rprint(f"  [green]Added: {source} --[{name}]--> {target}[/green]")
            except Exception as e:
                rprint(f"  [red]{e}[/red]")
        elif cmd == "remove-concept":
            concepts = list(onto.concepts.keys())
            if not concepts:
                rprint("  [yellow]No concepts to remove.[/yellow]")
                continue
            name = Prompt.ask("  Remove concept", choices=concepts)
            onto.remove_concept(name)
            rprint(f"  [red]Removed: {name}[/red]")
        elif cmd == "remove-relation":
            rels = list(onto.relations.keys())
            if not rels:
                rprint("  [yellow]No relations to remove.[/yellow]")
                continue
            name = Prompt.ask("  Remove relation", choices=rels)
            onto.remove_relation(name)
            rprint(f"  [red]Removed: {name}[/red]")
        else:
            rprint(
                "  [dim]Unknown command. Try: add-concept, add-property, "
                "add-relation, remove-concept, remove-relation, tree, done[/dim]"
            )

    return onto
