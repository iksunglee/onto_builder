"""Main CLI application."""

import typer

from ontobuilder.cli.concept_cmds import concept_app
from ontobuilder.cli.relation_cmds import relation_app

app = typer.Typer(
    name="onto",
    help="OntoBuilder — A beginner-friendly ontology builder.",
    no_args_is_help=True,
)

app.add_typer(concept_app, name="concept", help="Manage concepts.")
app.add_typer(relation_app, name="relation", help="Manage relations.")


# -- Top-level project commands --


@app.command()
def init(
    name: str = typer.Argument(..., help="Name of the ontology"),
):
    """Initialize a new ontology project in the current directory."""
    from pathlib import Path
    from ontobuilder.core.ontology import Ontology
    from ontobuilder.serialization.yaml_io import save_yaml
    from ontobuilder.cli.helpers import find_onto_file, DEFAULT_FILE

    existing = find_onto_file()
    if existing:
        typer.echo(f"An ontology file already exists: {existing.name}")
        raise typer.Exit(1)

    onto = Ontology(name)
    path = Path(DEFAULT_FILE)
    save_yaml(onto, path)
    typer.echo(f"Created '{path}' — ontology '{name}' is ready!")
    typer.echo("Next: try 'onto concept add Animal --description \"A living creature\"'")


@app.command()
def info():
    """Show summary information about the current ontology."""
    from rich import print as rprint
    from ontobuilder.cli.helpers import load_current_ontology

    onto, path = load_current_ontology()
    rprint(f"[bold]Ontology:[/bold] {onto.name}")
    if onto.description:
        rprint(f"  Description: {onto.description}")
    rprint(f"  File: {path}")
    rprint(f"  Concepts: {len(onto.concepts)}")
    rprint(f"  Relations: {len(onto.relations)}")
    rprint(f"  Instances: {len(onto.instances)}")


@app.command()
def save(
    file: str = typer.Argument(None, help="Output file path"),
):
    """Save the ontology to a file."""
    from pathlib import Path
    from ontobuilder.serialization.yaml_io import save_yaml
    from ontobuilder.cli.helpers import load_current_ontology

    onto, current_path = load_current_ontology()
    out = Path(file) if file else current_path
    save_yaml(onto, out)
    typer.echo(f"Saved to {out}")


@app.command()
def load(
    file: str = typer.Argument(..., help="Path to .onto.yaml file to load"),
):
    """Load an ontology from a file into the current directory."""
    from pathlib import Path
    from ontobuilder.serialization.yaml_io import load_yaml, save_yaml
    from ontobuilder.cli.helpers import DEFAULT_FILE

    src = Path(file)
    if not src.exists():
        typer.echo(f"File not found: {file}")
        raise typer.Exit(1)
    onto = load_yaml(src)
    dest = Path(DEFAULT_FILE)
    save_yaml(onto, dest)
    typer.echo(f"Loaded ontology '{onto.name}' from {file} → {dest}")


@app.command()
def export(
    format: str = typer.Option("yaml", "--format", "-f", help="Export format: yaml, json, prompt, jsonld, or schema-card"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Export the ontology to a specific format."""
    from pathlib import Path
    from ontobuilder.serialization.yaml_io import save_yaml
    from ontobuilder.serialization.json_io import save_json
    from ontobuilder.cli.helpers import load_current_ontology

    onto, path = load_current_ontology()
    if format == "json":
        out = Path(output) if output else path.with_suffix(".json")
        save_json(onto, out)
    elif format == "yaml":
        out = Path(output) if output else path
        save_yaml(onto, out)
    elif format == "prompt":
        from ontobuilder.serialization.prompt_io import save_prompt
        out = Path(output) if output else path.parent / "ontology.prompt.txt"
        save_prompt(onto, out)
    elif format == "jsonld":
        from ontobuilder.serialization.jsonld_io import save_jsonld
        out = Path(output) if output else path.parent / "ontology.jsonld"
        save_jsonld(onto, out)
    elif format == "schema-card":
        from ontobuilder.serialization.schemacard_io import save_schema_card
        out = Path(output) if output else path.parent / "ontology.schema-card.json"
        save_schema_card(onto, out)
    else:
        typer.echo(f"Unknown format: {format}. Use 'yaml', 'json', 'prompt', 'jsonld', or 'schema-card'.")
        raise typer.Exit(1)
    typer.echo(f"Exported to {out}")


@app.command()
def learn(
    term: str = typer.Argument(..., help="Term to look up (e.g., 'concept', 'relation')"),
):
    """Learn about ontology terms and concepts."""
    from rich import print as rprint
    from ontobuilder.education.glossary import get_definition

    definition = get_definition(term)
    if definition:
        rprint(f"\n[bold]{term.title()}[/bold]")
        rprint(f"  {definition}\n")
    else:
        from ontobuilder.education.glossary import GLOSSARY
        rprint(f"Term '{term}' not found. Available terms:")
        for t in sorted(GLOSSARY):
            rprint(f"  - {t}")


# -- Domain commands --

domains_app = typer.Typer(no_args_is_help=True)
app.add_typer(domains_app, name="domains", help="Domain templates.")


@domains_app.command("list")
def domains_list():
    """List available domain templates."""
    from rich import print as rprint
    from rich.table import Table
    from ontobuilder.domains.registry import list_builders

    builders = list_builders()
    if not builders:
        typer.echo("No domain templates available.")
        return
    table = Table(title="Available Domain Templates")
    table.add_column("Name", style="bold")
    table.add_column("Description")
    for b in builders:
        table.add_row(b.name, b.description)
    rprint(table)


@domains_app.command("apply")
def domains_apply(
    name: str = typer.Argument(..., help="Domain template name"),
):
    """Apply a domain template to create a pre-built ontology."""
    from pathlib import Path
    from rich import print as rprint
    from ontobuilder.domains.registry import get_builder
    from ontobuilder.serialization.yaml_io import save_yaml
    from ontobuilder.cli.helpers import DEFAULT_FILE

    builder = get_builder(name)
    if not builder:
        from ontobuilder.domains.registry import list_builders
        available = ", ".join(b.name for b in list_builders())
        typer.echo(f"Domain '{name}' not found. Available: {available}")
        raise typer.Exit(1)

    onto = builder.build_template()
    path = Path(DEFAULT_FILE)
    save_yaml(onto, path)
    rprint(f"Applied domain template '{name}' → {path}")
    rprint(onto.print_tree())


# -- LLM commands (lazy-loaded, only if deps installed) --


@app.command()
def interview(
    domain: str = typer.Option(None, "--domain", "-d", help="Domain template for hints"),
):
    """Start an AI-powered interview to build an ontology."""
    from ontobuilder.llm.interview import run_interview
    from ontobuilder.serialization.yaml_io import save_yaml
    from ontobuilder.cli.helpers import DEFAULT_FILE
    from pathlib import Path

    domain_hints = None
    if domain:
        from ontobuilder.domains.registry import get_builder
        builder = get_builder(domain)
        if builder:
            domain_hints = builder.get_interview_hints()

    onto = run_interview(domain_hints=domain_hints)
    if onto is None:
        return
    path = Path(DEFAULT_FILE)
    save_yaml(onto, path)
    typer.echo(f"Saved to {path}")


@app.command()
def infer(
    file: str = typer.Argument(..., help="Path to data file (CSV, JSON, or text)"),
):
    """Infer an ontology structure from a data file using AI."""
    from ontobuilder.llm.inference import infer_ontology
    from ontobuilder.serialization.yaml_io import save_yaml
    from ontobuilder.cli.helpers import DEFAULT_FILE
    from pathlib import Path

    onto = infer_ontology(file)
    if onto is None:
        return
    path = Path(DEFAULT_FILE)
    save_yaml(onto, path)
    typer.echo(f"Saved to {path}")


if __name__ == "__main__":
    app()
