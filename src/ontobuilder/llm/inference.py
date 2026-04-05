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
    """Infer ontology using local heuristic analysis — no LLM required."""
    from rich import print as rprint
    from rich.prompt import Confirm
    from rich.panel import Panel

    from ontobuilder.tool.analyzer import DataAnalyzer
    from ontobuilder.tool.suggestions import SuggestionEngine

    rprint(f"\n[bold]Analyzing data locally: {path.name}[/bold]\n")

    analyzer = DataAnalyzer()
    try:
        profile = analyzer.analyze(str(path))
    except (FileNotFoundError, ValueError) as e:
        rprint(f"[red]Error: {e}[/red]")
        return None

    engine = SuggestionEngine()
    suggestions = engine.suggest(profile)

    # Show what we found
    rprint(Panel(
        f"[bold]{profile.row_count}[/bold] rows, "
        f"[bold]{len(profile.columns)}[/bold] columns\n"
        f"Suggested main concept: [bold]{profile.suggested_concept_name}[/bold]",
        title=f"Data Profile: {path.name}",
        border_style="blue",
    ))

    rprint("[bold]Concepts:[/bold]")
    for cs in suggestions.concepts:
        source_label = {
            "main": "data file", "foreign_key": "foreign key",
            "categorical": "category", "nested": "nested object",
        }.get(cs.source, cs.source)
        props = ", ".join(f"{p.name}:{p.data_type}" for p in cs.properties)
        rprint(f"  - [bold]{cs.name}[/bold] [dim]({source_label})[/dim]"
               + (f"  [{props}]" if props else ""))

    if suggestions.relations:
        rprint("\n[bold]Relations:[/bold]")
        for rs in suggestions.relations:
            rprint(f"  - {rs.name}: {rs.source} → {rs.target}  ({rs.cardinality})")

    if suggestions.notes:
        rprint("\n[bold]Notes:[/bold]")
        for note in suggestions.notes:
            rprint(f"  [dim]{note}[/dim]")

    if not Confirm.ask("\nApply this ontology structure?", default=True):
        rprint("Cancelled.")
        return None

    onto_name = profile.suggested_concept_name + "Ontology"
    onto = engine.build_ontology(suggestions, onto_name)

    rprint("\n[bold green]Ontology built from data![/bold green]\n")
    rprint(onto.print_tree())

    return onto


def _infer_llm(path: Path) -> Ontology | None:
    """Infer ontology using LLM for richer semantic analysis."""
    from rich import print as rprint
    from rich.prompt import Confirm

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
        rprint(f"  {suggestion.description}\n")

    rprint("[bold]Concepts:[/bold]")
    for c in suggestion.concepts:
        parent = f" (child of {c.parent})" if c.parent else ""
        props = ", ".join(f"{p.name}:{p.data_type}" for p in c.properties)
        rprint(f"  - {c.name}{parent}" + (f"  [{props}]" if props else ""))

    rprint("\n[bold]Relations:[/bold]")
    for r in suggestion.relations:
        rprint(f"  - {r.name}: {r.source} → {r.target}")

    if not Confirm.ask("\nApply this ontology structure?", default=True):
        rprint("Cancelled.")
        return None

    onto = build_ontology_from_suggestion(suggestion)

    rprint("\n[bold green]Ontology built from data![/bold green]\n")
    rprint(onto.print_tree())

    return onto
