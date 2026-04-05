"""Main CLI application."""

import typer

from ontobuilder.cli.concept_cmds import concept_app
from ontobuilder.cli.relation_cmds import relation_app
from ontobuilder.cli.tool_cmds import tool_app

app = typer.Typer(
    name="ontobuilder",
    help="OntoBuilder - A beginner-friendly ontology builder.",
    no_args_is_help=True,
)

app.add_typer(concept_app, name="concept", help="Manage concepts.")
app.add_typer(relation_app, name="relation", help="Manage relations.")
app.add_typer(tool_app, name="tool", help="Analyze data and build OWL ontologies.")


# -- Top-level project commands --


def _read_env_file() -> dict[str, str]:
    """Read key=value pairs from .env file."""
    from pathlib import Path

    env_file = Path(".env")
    env_lines: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env_lines[k.strip()] = v.strip()
    return env_lines


def _write_env_file(env_lines: dict[str, str]) -> None:
    """Write key=value pairs to .env file and update os.environ."""
    import os
    from pathlib import Path

    env_file = Path(".env")
    env_file.write_text("\n".join(f"{k}={v}" for k, v in env_lines.items()) + "\n")
    for k, v in env_lines.items():
        os.environ[k] = v


def _test_llm_connection(provider: str, env_lines: dict[str, str]) -> str | None:
    """Test LLM connection. Returns None on success, error message on failure."""
    import os

    # Temporarily set env vars for the test
    old_env = {}
    for k, v in env_lines.items():
        old_env[k] = os.environ.get(k)
        os.environ[k] = v

    try:
        model = env_lines.get("ONTOBUILDER_LLM_MODEL", "gpt-4o-mini")
        test_msg = [{"role": "user", "content": "Say 'hello' in one word."}]

        if provider == "anthropic":
            from litellm import completion

            completion(model=model, messages=test_msg, max_tokens=10)
            return None

        if provider == "local":
            # First check if server is reachable
            import urllib.request
            import urllib.error

            base = env_lines.get("OPENAI_BASE_URL", "http://localhost:11434/v1")
            # Strip /v1 to check Ollama root
            root = base.replace("/v1", "")
            try:
                urllib.request.urlopen(root, timeout=5)
            except urllib.error.URLError:
                return (
                    f"Cannot reach local server at {root}\n"
                    "  Make sure Ollama is running: ollama serve\n"
                    "  Or check your LM Studio server is started."
                )

        # OpenAI, local, and custom all use OpenAI-compatible API
        from openai import OpenAI

        client_kwargs = {"api_key": env_lines.get("OPENAI_API_KEY", "not-needed")}
        if "OPENAI_BASE_URL" in env_lines:
            client_kwargs["base_url"] = env_lines["OPENAI_BASE_URL"]
        client = OpenAI(**client_kwargs)
        client.chat.completions.create(
            model=model, messages=test_msg, max_tokens=10
        )
        return None
    except Exception as e:
        return str(e)
    finally:
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _run_provider_wizard() -> bool:
    """Interactive provider setup wizard. Returns True if configured."""
    from rich import print as rprint
    from rich.panel import Panel
    from rich.prompt import Prompt

    rprint(
        Panel(
            "[bold]Choose your AI provider:[/bold]\n\n"
            "  [bold cyan][1][/bold cyan]  OpenAI            — GPT-4o-mini, GPT-4o  (needs API key)\n"
            "  [bold cyan][2][/bold cyan]  Anthropic (Claude) — Claude Sonnet, Haiku (needs API key)\n"
            "  [bold cyan][3][/bold cyan]  Local model        — Ollama, LM Studio    (free, runs on your machine)\n"
            "  [bold cyan][4][/bold cyan]  Custom endpoint    — Any OpenAI-compatible server",
            title="OntoBuilder — LLM Setup",
            border_style="blue",
        )
    )

    choice = Prompt.ask(
        "Provider",
        choices=["1", "2", "3", "4"],
        default="1",
    )

    env_lines = _read_env_file()

    if choice == "1":
        # OpenAI
        env_lines["ONTOBUILDER_PROVIDER"] = "openai"
        key = Prompt.ask("\nOpenAI API key [bold dim](sk-...)[/bold dim]").strip()
        if not key:
            rprint("[yellow]No API key provided. Aborting.[/yellow]")
            return False
        env_lines["OPENAI_API_KEY"] = key
        model = Prompt.ask(
            "Model", default="gpt-4o-mini",
        )
        env_lines["ONTOBUILDER_LLM_MODEL"] = model

    elif choice == "2":
        # Anthropic
        # Check litellm is installed
        try:
            import litellm  # noqa: F401
            import instructor  # noqa: F401
        except ImportError:
            rprint(
                "\n[red]Anthropic provider requires litellm.[/red]\n"
                "Install with: [bold]pip install ontobuilder[llm][/bold]"
            )
            return False

        env_lines["ONTOBUILDER_PROVIDER"] = "anthropic"
        env_lines["ONTOBUILDER_LLM_BACKEND"] = "litellm"
        key = Prompt.ask("\nAnthropic API key [bold dim](sk-ant-...)[/bold dim]").strip()
        if not key:
            rprint("[yellow]No API key provided. Aborting.[/yellow]")
            return False
        env_lines["ANTHROPIC_API_KEY"] = key
        rprint(
            "\n[dim]  Recommended models:[/dim]\n"
            "  [dim]  claude-sonnet-4-5-20250514 — fast & capable (default)[/dim]\n"
            "  [dim]  claude-haiku-4-5-20251001  — fastest & cheapest[/dim]\n"
            "  [dim]  claude-opus-4-5-20250527   — most capable[/dim]"
        )
        model = Prompt.ask(
            "Model", default="anthropic/claude-sonnet-4-5-20250514",
        )
        if not model.startswith("anthropic/"):
            model = f"anthropic/{model}"
        env_lines["ONTOBUILDER_LLM_MODEL"] = model

    elif choice == "3":
        # Local (Ollama / LM Studio)
        env_lines["ONTOBUILDER_PROVIDER"] = "local"
        rprint(
            "\n[bold]Local model setup[/bold]\n"
            "[dim]  Ollama:     Install from https://ollama.com then run: ollama serve[/dim]\n"
            "[dim]  LM Studio:  Start the local server from the app[/dim]\n"
        )
        base_url = Prompt.ask(
            "Server URL",
            default="http://localhost:11434/v1",
        )
        env_lines["OPENAI_BASE_URL"] = base_url
        env_lines["OPENAI_API_KEY"] = "not-needed"
        rprint(
            "\n[dim]  Popular models (install with: ollama pull <name>):[/dim]\n"
            "  [dim]  llama3.2       — 3B, fast, good general use[/dim]\n"
            "  [dim]  mistral        — 7B, strong reasoning[/dim]\n"
            "  [dim]  gemma2         — 9B, Google's open model[/dim]\n"
            "  [dim]  phi3           — 3.8B, Microsoft, very fast[/dim]"
        )
        model = Prompt.ask("Model", default="llama3.2")
        env_lines["ONTOBUILDER_LLM_MODEL"] = model

    elif choice == "4":
        # Custom endpoint
        env_lines["ONTOBUILDER_PROVIDER"] = "custom"
        base_url = Prompt.ask("\nEndpoint URL [bold dim](e.g. http://localhost:8080/v1)[/bold dim]")
        if not base_url.strip():
            rprint("[yellow]No endpoint provided. Aborting.[/yellow]")
            return False
        env_lines["OPENAI_BASE_URL"] = base_url.strip()
        key = Prompt.ask(
            "API key [bold dim](press Enter if none needed)[/bold dim]",
            default="not-needed",
        )
        env_lines["OPENAI_API_KEY"] = key
        model = Prompt.ask("Model name")
        if not model.strip():
            rprint("[yellow]No model name provided. Aborting.[/yellow]")
            return False
        env_lines["ONTOBUILDER_LLM_MODEL"] = model.strip()

    # Save configuration
    _write_env_file(env_lines)
    provider = env_lines.get("ONTOBUILDER_PROVIDER", "openai")
    rprint("\n[green]Configuration saved to .env[/green]")

    # Test connection
    rprint("Testing connection...")
    error = _test_llm_connection(provider, env_lines)
    if error:
        rprint(f"[yellow]Connection test failed:[/yellow] {error}")
        rprint("[dim]Settings saved — you can fix the issue and try again.[/dim]")
    else:
        rprint("[bold green]Connected successfully![/bold green]")

    return True


def _ensure_llm_configured() -> bool:
    """Check if LLM is configured; offer interactive setup if not.

    Call this at the top of any command that needs an LLM.
    Returns True if ready, False if user declined setup.
    """
    from ontobuilder.llm.client import is_configured

    if is_configured():
        return True

    from rich import print as rprint
    from rich.panel import Panel
    from rich.prompt import Confirm

    rprint(
        Panel(
            "[bold yellow]No LLM provider configured.[/bold yellow]\n\n"
            "OntoBuilder needs an AI model to power interviews, inference, and chat.\n"
            "You can use a cloud API (OpenAI, Claude) or a free local model (Ollama).\n\n"
            "Run [bold]ontobuilder configure[/bold] or set up now:",
            title="Setup Required",
            border_style="yellow",
        )
    )

    if Confirm.ask("Set up LLM provider now?", default=True):
        return _run_provider_wizard()

    rprint("[dim]Run 'ontobuilder configure' when you're ready.[/dim]")
    return False


@app.command()
def configure(
    api_key: str = typer.Option(None, "--api-key", "-k", help="API key"),
    model: str = typer.Option(None, "--model", "-m", help="LLM model name"),
    provider: str = typer.Option(
        None, "--provider", "-p", help="Provider: openai, anthropic, local, custom"
    ),
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
):
    """Configure LLM settings — choose your AI provider."""
    import os
    from rich import print as rprint
    from rich.panel import Panel

    if show:
        prov = os.environ.get("ONTOBUILDER_PROVIDER", "(not set)")
        current_key = (
            os.environ.get("ONTOBUILDER_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
        )
        current_model = os.environ.get("ONTOBUILDER_LLM_MODEL", "gpt-4o-mini")
        backend = os.environ.get("ONTOBUILDER_LLM_BACKEND", "auto")
        base_url = os.environ.get("OPENAI_BASE_URL", "(default)")

        if current_key and len(current_key) > 8:
            masked = f"{current_key[:6]}...{current_key[-4:]}"
        elif current_key:
            masked = "***"
        else:
            masked = "[red](not set)[/red]"

        # Check installed backends
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
            Panel(
                f"[bold]Provider:[/bold]  {prov}\n"
                f"[bold]API Key:[/bold]   {masked}\n"
                f"[bold]Model:[/bold]     {current_model}\n"
                f"[bold]Backend:[/bold]   {backend}\n"
                f"[bold]Base URL:[/bold]  {base_url}\n"
                f"[bold]Installed:[/bold] "
                f"{', '.join(backends) if backends else '[red]none[/red]'}",
                title="Current LLM Configuration",
                border_style="blue",
            )
        )
        return

    # Non-interactive: flags provided
    if api_key or model or provider:
        env_lines = _read_env_file()
        if provider:
            env_lines["ONTOBUILDER_PROVIDER"] = provider
            if provider == "anthropic":
                env_lines["ONTOBUILDER_LLM_BACKEND"] = "litellm"
        if api_key:
            prov = provider or env_lines.get("ONTOBUILDER_PROVIDER", "openai")
            if prov == "anthropic":
                env_lines["ANTHROPIC_API_KEY"] = api_key
            else:
                env_lines["OPENAI_API_KEY"] = api_key
        if model:
            env_lines["ONTOBUILDER_LLM_MODEL"] = model
        _write_env_file(env_lines)
        rprint("[green]Configuration saved to .env[/green]")
        return

    # Interactive wizard
    _run_provider_wizard()


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
    typer.echo("Next: try 'ontobuilder concept add Animal --description \"A living creature\"'")


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
    if not _ensure_llm_configured():
        raise typer.Exit(1)

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
    file: str = typer.Argument(None, help="Path to data file (CSV, JSON, or text)"),
    local: bool = typer.Option(
        False, "--local", "-l",
        help="Use local heuristic analysis (no LLM or API key needed)",
    ),
    text: str = typer.Option(
        None, "--text", "-t",
        help="Inline text/data to infer from (instead of a file)",
    ),
    stdin: bool = typer.Option(
        False, "--stdin",
        help="Read data from stdin (pipe or paste, end with Ctrl+D)",
    ),
):
    """Infer an ontology structure from data.

    Provide data as a file path, inline text, or via stdin.
    Uses AI by default; use --local for fast offline analysis (CSV/JSON files only).

    Examples:
      ontobuilder infer data.csv --local
      ontobuilder infer data.json
      ontobuilder infer --text "name,age,role\\nAlice,30,Engineer\\nBob,25,Designer"
      cat data.csv | ontobuilder infer --stdin
    """
    import sys
    import tempfile
    from pathlib import Path

    from ontobuilder.serialization.yaml_io import save_yaml
    from ontobuilder.cli.helpers import DEFAULT_FILE

    # Resolve input source
    if text:
        # Write inline text to a temp file so the inference pipeline can read it
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        )
        tmp.write(text.replace("\\n", "\n"))
        tmp.close()
        file = tmp.name
    elif stdin:
        data = sys.stdin.read()
        if not data.strip():
            typer.echo("No data received on stdin.")
            raise typer.Exit(1)
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        )
        tmp.write(data)
        tmp.close()
        file = tmp.name
    elif file is None:
        typer.echo("Provide a file path, --text, or --stdin. See: ontobuilder infer --help")
        raise typer.Exit(1)

    if not local and not _ensure_llm_configured():
        raise typer.Exit(1)

    from ontobuilder.llm.inference import infer_ontology

    onto = infer_ontology(file, local=local)
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
            "Usage: ontobuilder owl query <classes|instances|relations|describe|validate|path> [name] [options]"
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
    if not _ensure_llm_configured():
        raise typer.Exit(1)

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
