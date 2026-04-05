"""CLI commands for managing relations."""

from typing import Optional

import typer
from rich import print as rprint
from rich.table import Table

from ontobuilder.cli.helpers import load_current_ontology, save_current_ontology
from ontobuilder.core.validation import ValidationError

relation_app = typer.Typer(no_args_is_help=True)


@relation_app.command("add")
def add_relation(
    name: str,
    source: str = typer.Option(..., "--from", help="Source concept"),
    target: str = typer.Option(..., "--to", help="Target concept"),
    cardinality: str = typer.Option("many-to-many", "--cardinality", "-c"),
):
    """Add a relation between two concepts."""
    onto, path = load_current_ontology()
    try:
        onto.add_relation(name, source=source, target=target, cardinality=cardinality)
    except ValidationError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)
    save_current_ontology(onto, path)
    typer.echo(f"Added relation '{name}': {source} -> {target}")


@relation_app.command("list")
def list_relations():
    """List all relations."""
    onto, _ = load_current_ontology()
    if not onto.relations:
        typer.echo("No relations yet.")
        return
    table = Table(title=f"Relations in '{onto.name}'")
    table.add_column("Name", style="bold")
    table.add_column("Source")
    table.add_column("Target")
    table.add_column("Cardinality")
    for r in onto.relations.values():
        table.add_row(r.name, r.source, r.target, r.cardinality)
    rprint(table)


@relation_app.command("remove")
def remove_relation(name: str):
    """Remove a relation."""
    onto, path = load_current_ontology()
    try:
        onto.remove_relation(name)
    except ValidationError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)
    save_current_ontology(onto, path)
    typer.echo(f"Removed relation '{name}'.")
