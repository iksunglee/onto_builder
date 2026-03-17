"""CLI commands for managing concepts."""

from typing import Optional

import typer
from rich import print as rprint
from rich.table import Table

from ontobuilder.cli.helpers import load_current_ontology, save_current_ontology
from ontobuilder.core.validation import ValidationError

concept_app = typer.Typer(no_args_is_help=True)


@concept_app.command("add")
def add_concept(
    name: str,
    parent: Optional[str] = typer.Option(None, "--parent", "-p", help="Parent concept name"),
    description: str = typer.Option("", "--description", "-d", help="Description of the concept"),
):
    """Add a new concept to the ontology."""
    onto, path = load_current_ontology()
    try:
        onto.add_concept(name, description=description, parent=parent)
    except ValidationError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)
    save_current_ontology(onto, path)
    msg = f"Added concept '{name}'"
    if parent:
        msg += f" (child of '{parent}')"
    typer.echo(msg)


@concept_app.command("list")
def list_concepts(
    tree: bool = typer.Option(False, "--tree", "-t", help="Show as tree"),
):
    """List all concepts."""
    onto, _ = load_current_ontology()
    if not onto.concepts:
        typer.echo("No concepts yet.")
        return

    if tree:
        rprint(onto.print_tree())
    else:
        table = Table(title=f"Concepts in '{onto.name}'")
        table.add_column("Name", style="bold")
        table.add_column("Parent")
        table.add_column("Description")
        table.add_column("Properties")
        for c in onto.concepts.values():
            props = ", ".join(p.name for p in c.properties) if c.properties else "—"
            table.add_row(c.name, c.parent or "—", c.description or "—", props)
        rprint(table)


@concept_app.command("show")
def show_concept(name: str):
    """Show details of a concept."""
    onto, _ = load_current_ontology()
    if name not in onto.concepts:
        typer.echo(f"Concept '{name}' not found.")
        raise typer.Exit(1)
    c = onto.concepts[name]
    rprint(f"[bold]{c.name}[/bold]")
    if c.description:
        rprint(f"  Description: {c.description}")
    if c.parent:
        rprint(f"  Parent: {c.parent}")
    if c.properties:
        rprint("  Properties:")
        for p in c.properties:
            req = " (required)" if p.required else ""
            rprint(f"    - {p.name}: {p.data_type}{req}")
    # Show children
    children = [ch for ch in onto.concepts.values() if ch.parent == name]
    if children:
        rprint("  Children: " + ", ".join(ch.name for ch in children))


@concept_app.command("remove")
def remove_concept(name: str):
    """Remove a concept from the ontology."""
    onto, path = load_current_ontology()
    try:
        onto.remove_concept(name)
    except ValidationError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)
    save_current_ontology(onto, path)
    typer.echo(f"Removed concept '{name}'.")
