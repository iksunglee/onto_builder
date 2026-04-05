"""Shared CLI helpers."""

from __future__ import annotations

from pathlib import Path

from ontobuilder.core.ontology import Ontology
from ontobuilder.serialization.yaml_io import save_yaml, load_yaml

DEFAULT_FILE = "ontology.onto.yaml"


def find_onto_file(directory: str | Path = ".") -> Path | None:
    """Find the .onto.yaml file in the given directory."""
    d = Path(directory)
    for f in d.iterdir():
        if f.name.endswith(".onto.yaml"):
            return f
    return None


def load_current_ontology() -> tuple[Ontology, Path]:
    """Load the ontology from the current directory."""
    path = find_onto_file()
    if path is None:
        import typer
        typer.echo("No .onto.yaml file found. Run 'ontobuilder init <name>' first.")
        raise typer.Exit(1)
    return load_yaml(path), path


def save_current_ontology(onto: Ontology, path: Path) -> None:
    """Save the ontology back to disk."""
    save_yaml(onto, path)
