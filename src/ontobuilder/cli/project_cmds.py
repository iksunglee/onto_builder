"""CLI commands for project-level operations (init, save, load, export, info)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

from ontobuilder.core.ontology import Ontology
from ontobuilder.serialization.yaml_io import save_yaml, load_yaml
from ontobuilder.serialization.json_io import save_json
from ontobuilder.cli.helpers import (
    DEFAULT_FILE,
    find_onto_file,
    load_current_ontology,
    save_current_ontology,
)

# We store commands as (name, command) tuples so app.py can register them
# on the top-level Typer app.
_commands: list[tuple[str, typer.models.CommandInfo]] = []

project_app = type("_ProjectCommands", (), {"registered_commands": _commands})()


def _register(name: str):
    """Decorator to register a command."""
    def decorator(func):
        info = typer.models.CommandInfo(name=name, callback=func)
        _commands.append((name, info))
        return func
    return decorator


@_register("init")
def init_project(
    name: str = typer.Argument(..., help="Name of the ontology"),
):
    """Initialize a new ontology project in the current directory."""
    existing = find_onto_file()
    if existing:
        typer.echo(f"An ontology file already exists: {existing.name}")
        raise typer.Exit(1)

    onto = Ontology(name)
    path = Path(DEFAULT_FILE)
    save_yaml(onto, path)
    typer.echo(f"Created '{path}' — ontology '{name}' is ready!")
    typer.echo("Next: try 'onto concept add Animal --description \"A living creature\"'")


@_register("info")
def info():
    """Show summary information about the current ontology."""
    onto, path = load_current_ontology()
    rprint(f"[bold]Ontology:[/bold] {onto.name}")
    if onto.description:
        rprint(f"  Description: {onto.description}")
    rprint(f"  File: {path}")
    rprint(f"  Concepts: {len(onto.concepts)}")
    rprint(f"  Relations: {len(onto.relations)}")
    rprint(f"  Instances: {len(onto.instances)}")


@_register("save")
def save(
    file: str = typer.Argument(None, help="Output file path"),
):
    """Save the ontology to a file."""
    onto, current_path = load_current_ontology()
    out = Path(file) if file else current_path
    save_yaml(onto, out)
    typer.echo(f"Saved to {out}")


@_register("load")
def load(
    file: str = typer.Argument(..., help="Path to .onto.yaml file to load"),
):
    """Load an ontology from a file into the current directory."""
    src = Path(file)
    if not src.exists():
        typer.echo(f"File not found: {file}")
        raise typer.Exit(1)
    onto = load_yaml(src)
    dest = Path(DEFAULT_FILE)
    save_yaml(onto, dest)
    typer.echo(f"Loaded ontology '{onto.name}' from {file} → {dest}")


@_register("export")
def export(
    format: str = typer.Option("yaml", "--format", "-f", help="Export format: yaml or json"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Export the ontology to a specific format."""
    onto, path = load_current_ontology()
    if format == "json":
        out = Path(output) if output else path.with_suffix(".json")
        save_json(onto, out)
    elif format == "yaml":
        out = Path(output) if output else path
        save_yaml(onto, out)
    else:
        typer.echo(f"Unknown format: {format}. Use 'yaml' or 'json'.")
        raise typer.Exit(1)
    typer.echo(f"Exported to {out}")
