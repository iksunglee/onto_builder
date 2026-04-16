"""CLI commands for improving ontology quality."""

from __future__ import annotations

import json

import typer
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table

improve_app = typer.Typer(no_args_is_help=True)


@improve_app.command()
def audit(
    output: str = typer.Option(None, "--output", "-o", help="Save report to JSON file"),
    format: str = typer.Option("rich", "--format", "-f", help="Output format: rich or json"),
):
    """Run quality checks on the ontology and show a scored report."""
    from pathlib import Path

    from ontobuilder.cli.helpers import load_current_ontology
    from ontobuilder.tool.audit import OntologyAuditor

    onto, _path = load_current_ontology()
    auditor = OntologyAuditor()
    result = auditor.audit(onto)

    if format == "json" or output:
        data = result.to_dict()
        if output:
            Path(output).write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            rprint(f"[green]Report saved to {output}[/green]")
        else:
            typer.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    # Rich output
    if result.score >= 80:
        color = "green"
    elif result.score >= 50:
        color = "yellow"
    else:
        color = "red"

    rprint(
        Panel(
            f"[bold {color}]{result.summary}[/bold {color}]",
            title=f"Ontology Audit: {onto.name}",
            border_style=color,
        )
    )

    if not result.items:
        rprint("[green]No issues found.[/green]")
        return

    table = Table(title="Findings")
    table.add_column("Severity", style="bold", width=10)
    table.add_column("Check", width=25)
    table.add_column("Detail")

    severity_style = {
        "CRITICAL": "bold red",
        "WARNING": "yellow",
        "SUGGESTION": "dim",
    }

    for item in result.items:
        table.add_row(
            f"[{severity_style.get(item.severity, '')}]{item.severity}[/]",
            item.check,
            item.detail,
        )

    rprint(table)


@improve_app.command()
def compare(
    file: str = typer.Argument(..., help="Path to second .onto.yaml file to compare against"),
    output: str = typer.Option(None, "--output", "-o", help="Save diff to JSON file"),
    merge: bool = typer.Option(False, "--merge", help="Merge the second file into the current ontology"),
    format: str = typer.Option("rich", "--format", "-f", help="Output format: rich or json"),
):
    """Compare the current ontology with another .onto.yaml file."""
    from pathlib import Path

    from ontobuilder.cli.helpers import load_current_ontology, save_current_ontology
    from ontobuilder.serialization.yaml_io import load_yaml
    from ontobuilder.tool.compare import diff_ontologies, merge_ontologies

    onto_a, onto_path = load_current_ontology()

    file_path = Path(file)
    if not file_path.exists():
        rprint(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)
    onto_b = load_yaml(file_path)

    diff = diff_ontologies(onto_a, onto_b)

    # Always perform merge when requested, regardless of output format
    if merge:
        merged = merge_ontologies(onto_a, onto_b)
        save_current_ontology(merged, onto_path)

    if format == "json" or (output and not merge):
        data = diff.to_dict()
        if output:
            Path(output).write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            rprint(f"[green]Diff saved to {output}[/green]")
        else:
            typer.echo(json.dumps(data, indent=2, ensure_ascii=False))
        if merge:
            rprint(f"\n[bold green]Merged! Saved to {onto_path}[/bold green]")
            rprint(
                f"  Concepts: {len(merged.concepts)}, "
                f"Relations: {len(merged.relations)}, "
                f"Instances: {len(merged.instances)}"
            )
        return

    # Rich output
    rprint(
        Panel(
            f"[bold]{diff.summary}[/bold]\n\n"
            f"A: {onto_a.name} ({onto_path.name})\n"
            f"B: {onto_b.name} ({file_path.name})",
            title="Ontology Diff",
            border_style="blue",
        )
    )

    if diff.only_in_a.concepts or diff.only_in_a.relations or diff.only_in_a.instances:
        rprint(f"\n[bold cyan]Only in A ({onto_path.name}):[/bold cyan]")
        for c in diff.only_in_a.concepts:
            rprint(f"  concept: {c}")
        for r in diff.only_in_a.relations:
            rprint(f"  relation: {r}")
        for i in diff.only_in_a.instances:
            rprint(f"  instance: {i}")

    if diff.only_in_b.concepts or diff.only_in_b.relations or diff.only_in_b.instances:
        rprint(f"\n[bold magenta]Only in B ({file_path.name}):[/bold magenta]")
        for c in diff.only_in_b.concepts:
            rprint(f"  concept: {c}")
        for r in diff.only_in_b.relations:
            rprint(f"  relation: {r}")
        for i in diff.only_in_b.instances:
            rprint(f"  instance: {i}")

    if diff.modified:
        rprint("\n[bold yellow]Modified:[/bold yellow]")
        for mod in diff.modified:
            rprint(f"  {mod['type']}: {mod['name']}")
            for k, v in mod.items():
                if k not in ("name", "type"):
                    rprint(f"    {k}: {v}")

    if merge:
        rprint(f"\n[bold green]Merged! Saved to {onto_path}[/bold green]")
        rprint(
            f"  Concepts: {len(merged.concepts)}, "
            f"Relations: {len(merged.relations)}, "
            f"Instances: {len(merged.instances)}"
        )
