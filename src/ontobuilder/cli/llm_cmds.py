"""CLI commands for LLM-powered features."""

from typing import Optional

import typer
from rich import print as rprint

from ontobuilder.cli.helpers import (
    DEFAULT_FILE,
)
from ontobuilder.serialization.yaml_io import save_yaml

llm_app = typer.Typer(no_args_is_help=True)


@llm_app.command("interview")
def interview(
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Domain template to use"),
):
    """Start an interactive interview to build an ontology with AI assistance."""
    from ontobuilder.llm.interview import run_interview

    domain_hints = None
    if domain:
        try:
            from ontobuilder.domains.registry import get_builder
            builder = get_builder(domain)
            if builder:
                domain_hints = builder.get_interview_hints()
        except ImportError:
            pass

    onto = run_interview(domain_hints=domain_hints)
    if onto is None:
        return

    from pathlib import Path
    path = Path(DEFAULT_FILE)
    save_yaml(onto, path)
    rprint(f"\n[bold]Saved to {path}[/bold]")


@llm_app.command("infer")
def infer(
    file: str = typer.Argument(..., help="Path to data file (CSV, JSON, or text)"),
):
    """Infer an ontology structure from a data file."""
    from ontobuilder.llm.inference import infer_ontology

    onto = infer_ontology(file)
    if onto is None:
        return

    from pathlib import Path
    path = Path(DEFAULT_FILE)
    save_yaml(onto, path)
    rprint(f"\n[bold]Saved to {path}[/bold]")
