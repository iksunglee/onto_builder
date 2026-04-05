"""Main CLI application."""

import typer

from ontobuilder.cli.concept_cmds import concept_app
from ontobuilder.cli.relation_cmds import relation_app
from ontobuilder.cli.tool_cmds import tool_app

app = typer.Typer(
    name="onto",
    help="OntoBuilder - A beginner-friendly ontology builder.",
    no_args_is_help=True,
)

app.add_typer(concept_app, name="concept", help="Manage concepts.")
app.add_typer(relation_app, name="relation", help="Manage relations.")
app.add_typer(tool_app, name="tool", help="Analyze data and build OWL ontologies.")


# -- Top-level project commands --


@app.command()
def configure(
    api_key: str = typer.Option(None, "--api-key", "-k", help="OpenAI API key"),
    model: str = typer.Option(
        None, "--model", "-m", help="LLM model name (e.g., gpt-4o-mini, gpt-4o)"
    ),
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
):
    """Configure LLM settings (API key, model)."""
    import os
    from pathlib import Path
    from rich import print as rprint

    env_file = Path(".env")

    if show:
        current_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ONTOBUILDER_API_KEY")
        current_model = os.environ.get("ONTOBUILDER_LLM_MODEL", "gpt-4o-mini")
        backend = os.environ.get("ONTOBUILDER_LLM_BACKEND", "auto")
        masked = (
            f"sk-...{current_key[-4:]}" if current_key and len(current_key) > 4 else "(not set)"
        )
        rprint(f"[bold]API Key:[/bold]  {masked}")
        rprint(f"[bold]Model:[/bold]    {current_model}")
        rprint(f"[bold]Backend:[/bold]  {backend}")

        # Check what's installed
        backends = []
        try:
            import openai  # noqa: F401

            backends.append("openai")
        except ImportError:
            pass
        try:
            import litellm  # noqa: F401
            import instructor  # noqa: F401

            backends.append("litellm+instructor")
        except ImportError:
            pass
        rprint(
            f"[bold]Installed:[/bold] {', '.join(backends) if backends else '[red]none[/red] (pip install openai)'}"
        )
        return

    # Interactive setup if no flags
    if not api_key and not model:
        rprint("[bold]OntoBuilder LLM Configuration[/bold]\n")
        api_key = input("OpenAI API key (sk-...): ").strip()
        model_input = input("Model name [gpt-4o-mini]: ").strip()
        if model_input:
            model = model_input

    # Write to .env file
    env_lines = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env_lines[k.strip()] = v.strip()

    if api_key:
        env_lines["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_API_KEY"] = api_key
    if model:
        env_lines["ONTOBUILDER_LLM_MODEL"] = model
        os.environ["ONTOBUILDER_LLM_MODEL"] = model

    env_file.write_text("\n".join(f"{k}={v}" for k, v in env_lines.items()) + "\n")
    rprint(f"[green]Configuration saved to {env_file}[/green]")

    # Verify connection
    if api_key:
        rprint("\nTesting connection...")
        try:
            from ontobuilder.llm.openai_client import get_client

            client = get_client(api_key)
            resp = client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=[{"role": "user", "content": "Say 'ok' in one word."}],
                max_tokens=5,
            )
            rprint(f"[green]Connected! Response: {resp.choices[0].message.content}[/green]")
        except Exception as e:
            rprint(f"[yellow]Connection test failed: {e}[/yellow]")
            rprint("The key was saved - you can test again later.")


@app.command()
def init(
    name: str = typer.Argument(..., help="Name of the ontology"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing ontology file in the current directory.",
    ),
):
    """Initialize a new ontology project in the current directory."""
    from pathlib import Path
    from ontobuilder.core.ontology import Ontology
    from ontobuilder.serialization.yaml_io import save_yaml
    from ontobuilder.cli.helpers import find_onto_file, DEFAULT_FILE

    existing = find_onto_file()
    if existing and not force:
        typer.echo(
            f"An ontology file already exists: {existing.name}. "
            "Use --force to overwrite it, or run init in a new directory."
        )
        raise typer.Exit(1)

    onto = Ontology(name)
    path = existing if existing and force else Path(DEFAULT_FILE)
    save_yaml(onto, path)
    typer.echo(f"Created '{path}' - ontology '{name}' is ready!")
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
    typer.echo(f"Loaded ontology '{onto.name}' from {file} -> {dest}")


@app.command()
def export(
    format: str = typer.Option(
        "yaml", "--format", "-f", help="Export format: yaml, json, prompt, jsonld, or schema-card"
    ),
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
    elif format in ("owl", "owl-xml"):
        from ontobuilder.owl.export import save_owl

        out = Path(output) if output else path.parent / "ontology.owl"
        save_owl(onto, out, fmt="xml")
    elif format == "turtle":
        from ontobuilder.owl.export import save_owl

        out = Path(output) if output else path.parent / "ontology.ttl"
        save_owl(onto, out, fmt="turtle")
    else:
        typer.echo(
            f"Unknown format: {format}. Use 'yaml', 'json', 'prompt', 'jsonld', 'schema-card', 'owl', or 'turtle'."
        )
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


@app.command()
def suggest(
    limit: int = typer.Option(
        5, "--limit", "-n", min=1, max=10, help="Maximum suggestions to show"
    ),
):
    """Infer likely next actions based on current ontology state."""
    from rich import print as rprint
    from ontobuilder.chat.checker import OntologyChat
    from ontobuilder.cli.helpers import load_current_ontology

    onto, _ = load_current_ontology()
    checker = OntologyChat(onto)
    suggestions = checker.infer_user_intent(limit=limit)

    rprint("[bold]Likely next actions based on your ontology:[/bold]")
    for i, suggestion in enumerate(suggestions, start=1):
        rprint(f"{i}. {suggestion}")


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
    rprint(f"Applied domain template '{name}' -> {path}")
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


# -- OWL commands --

owl_app = typer.Typer(no_args_is_help=True)
app.add_typer(owl_app, name="owl", help="OWL export, reasoning, and queries.")


@owl_app.command("export")
def owl_export(
    format: str = typer.Option("xml", "--format", "-f", help="OWL format: xml or turtle"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Export ontology as OWL/RDF (RDF-XML or Turtle)."""
    from pathlib import Path
    from ontobuilder.owl.export import save_owl
    from ontobuilder.cli.helpers import load_current_ontology

    onto, path = load_current_ontology()
    if format == "turtle":
        default_ext = ".ttl"
    else:
        default_ext = ".owl"
    out = Path(output) if output else path.parent / f"ontology{default_ext}"
    save_owl(onto, out, fmt=format)
    typer.echo(f"Exported OWL ({format}) to {out}")


@owl_app.command("reason")
def owl_reason():
    """Run OWL inference and consistency checks on the ontology."""
    from rich import print as rprint
    from rich.panel import Panel
    from ontobuilder.owl.reasoning import OWLReasoner
    from ontobuilder.cli.helpers import load_current_ontology

    onto, _ = load_current_ontology()
    reasoner = OWLReasoner(onto)
    result = reasoner.run_inference()

    rprint(
        Panel(
            result.summary,
            title="Inference Results",
            border_style="green" if result.is_consistent else "red",
        )
    )

    if result.inferred_subclasses:
        rprint("\n[bold]Inferred Subclass Chains:[/bold]")
        for cls, ancestors in result.inferred_subclasses.items():
            rprint(f"  {cls} -> {' -> '.join(ancestors)}")

    if result.inherited_properties:
        rprint("\n[bold]Inherited Properties:[/bold]")
        for cls, props in result.inherited_properties.items():
            rprint(f"  {cls}:")
            for p in props:
                rprint(f"    - {p}")

    if result.instance_types:
        rprint("\n[bold]Instance Classification:[/bold]")
        for inst, types in result.instance_types.items():
            rprint(f"  {inst} in {{{', '.join(types)}}}")


@owl_app.command("query")
def owl_query(
    query_type: str = typer.Argument(
        ..., help="Query type: classes, instances, relations, describe, validate, path"
    ),
    name: str = typer.Argument(None, help="Class/instance name (for describe, validate, path)"),
    target: str = typer.Option(None, "--target", "-t", help="Target class (for path queries)"),
    parent: str = typer.Option(None, "--parent", "-p", help="Filter by parent class"),
    of_class: str = typer.Option(None, "--class", "-c", help="Filter by class (for instances)"),
):
    """Run structured queries against the ontology."""
    from rich import print as rprint
    from ontobuilder.owl.query import StructuredQuery
    from ontobuilder.cli.helpers import load_current_ontology

    onto, _ = load_current_ontology()
    engine = StructuredQuery(onto)

    if query_type == "classes":
        result = engine.find_classes(parent=parent, name_contains=name)
    elif query_type == "instances":
        result = engine.find_instances(of_class=of_class or name)
    elif query_type == "relations":
        result = engine.find_relations(source=name, target=target)
    elif query_type == "describe" and name:
        result = engine.describe_class(name)
    elif query_type == "validate" and name:
        result = engine.validate_instance(name)
    elif query_type == "path" and name and target:
        result = engine.find_path(name, target)
    else:
        typer.echo(
            "Usage: onto owl query <classes|instances|relations|describe|validate|path> [name] [options]"
        )
        raise typer.Exit(1)

    rprint(result.to_table())


# -- Chat command --


@app.command()
def chat(
    question: str = typer.Argument(None, help="Question to ask (omit for interactive mode)"),
):
    """Chat with your ontology - ask questions in natural language."""
    from rich import print as rprint
    from rich.panel import Panel
    from ontobuilder.chat.checker import OntologyChat
    from ontobuilder.cli.helpers import load_current_ontology

    onto, _ = load_current_ontology()
    checker = OntologyChat(onto)

    if question:
        answer = checker.ask(question)
        rprint(Panel(answer, title="Answer", border_style="blue"))
        return

    # Interactive mode
    rprint(
        Panel(
            f"Chatting with ontology '{onto.name}' ({len(onto.concepts)} classes, "
            f"{len(onto.relations)} relations, {len(onto.instances)} instances)\n"
            "Type 'quit' or 'exit' to stop.",
            title="Ontology Chat",
            border_style="blue",
        )
    )

    while True:
        try:
            q = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() in ("quit", "exit", "q"):
            break
        answer = checker.ask(q)
        rprint(f"\n[bold blue]Assistant:[/bold blue] {answer}")


# -- Workspace command (data -> infer -> chat-refine -> OWL export) --


@app.command()
def workspace(
    file: str = typer.Argument(
        None, help="Data file to analyze (CSV, JSON, text). Omit to use current ontology."
    ),
    output: str = typer.Option(None, "--output", "-o", help="Auto-save OWL file on exit"),
):
    """Open a live workspace: analyze data, build ontology, refine via chat, export OWL."""
    from pathlib import Path
    from rich import print as rprint
    from rich.panel import Panel

    if file:
        # Data-first mode: analyze file with LLM
        rprint(f"\n[bold]Analyzing data from: {file}[/bold]")
        rprint("Sending to LLM for ontology inference...\n")

        from ontobuilder.chat.workspace import OntologyWorkspace

        try:
            ws = OntologyWorkspace.from_data(file)
        except ImportError:
            rprint("[red]LLM features require: pip install ontobuilder[llm][/red]")
            raise typer.Exit(1)
        except FileNotFoundError as e:
            rprint(f"[red]{e}[/red]")
            raise typer.Exit(1)
    else:
        # Load existing ontology
        from ontobuilder.cli.helpers import load_current_ontology
        from ontobuilder.chat.workspace import OntologyWorkspace

        onto, _ = load_current_ontology()
        ws = OntologyWorkspace.from_existing(onto)

    # Show initial state
    rprint(
        Panel(
            f"[bold]{ws.onto.name}[/bold]\n"
            f"{len(ws.onto.concepts)} classes, {len(ws.onto.relations)} relations, "
            f"{len(ws.onto.instances)} instances\n\n"
            f"{ws.onto.print_tree()}",
            title="Base Ontology Generated",
            border_style="green",
        )
    )

    rprint(
        Panel(
            "Chat commands:\n"
            "  Type naturally to ask questions or request changes\n"
            "  'show'     - show current ontology state\n"
            "  'tree'     - show class hierarchy\n"
            "  'check'    - run inference & consistency check\n"
            "  'owl'      - preview OWL Turtle output\n"
            "  'log'      - show edit history\n"
            "  'save'     - save to OWL file\n"
            "  'quit'     - exit workspace",
            title="Workspace Chat",
            border_style="blue",
        )
    )

    while True:
        try:
            msg = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not msg:
            continue
        if msg.lower() in ("quit", "exit", "q"):
            break

        # Built-in workspace commands
        if msg.lower() == "show":
            rprint(f"\n{ws.get_state()}")
            continue
        if msg.lower() == "tree":
            rprint(f"\n{ws.onto.print_tree()}")
            continue
        if msg.lower() == "check":
            rprint(f"\n{ws.run_inference()}")
            continue
        if msg.lower() == "owl":
            rprint(f"\n[dim]{ws.export_owl('turtle')}[/dim]")
            continue
        if msg.lower() == "log":
            for entry in ws.get_edit_log():
                rprint(f"  {entry}")
            continue
        if msg.lower() == "save":
            out = Path(output) if output else Path("ontology.ttl")
            ws.save_owl(out, fmt="turtle")
            rprint(f"[green]Saved to {out}[/green]")
            continue

        # Send to LLM for processing
        try:
            result = ws.ask(msg)
        except ImportError:
            rprint("[red]LLM features require: pip install ontobuilder[llm][/red]")
            continue
        except Exception as e:
            rprint(f"[red]Error: {e}[/red]")
            continue

        # Show response
        rprint(f"\n[bold blue]Assistant:[/bold blue] {result['explanation']}")

        if result["edits_applied"]:
            rprint("\n[bold green]Changes applied:[/bold green]")
            for edit in result["edits_applied"]:
                rprint(f"  + {edit}")

        if result["errors"]:
            rprint("\n[bold red]Errors:[/bold red]")
            for err in result["errors"]:
                rprint(f"  ! {err}")

        rprint(f"\n[dim]State: {result['ontology_state']}[/dim]")

    # Auto-save on exit if requested
    if output:
        out = Path(output)
        ws.save_owl(out, fmt="turtle")
        rprint(f"\n[green]Saved to {out}[/green]")

    # Also save to YAML for the onto ecosystem
    from ontobuilder.serialization.yaml_io import save_yaml
    from ontobuilder.cli.helpers import DEFAULT_FILE

    save_yaml(ws.onto, Path(DEFAULT_FILE))
    rprint(f"Ontology saved to {DEFAULT_FILE}")


if __name__ == "__main__":
    app()
