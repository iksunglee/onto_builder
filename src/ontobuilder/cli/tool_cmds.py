"""CLI commands for the data analysis and ontology building tool."""

from __future__ import annotations

from pathlib import Path

import typer
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table


tool_app = typer.Typer(no_args_is_help=True)


@tool_app.command("analyze")
def tool_analyze(
    file: str = typer.Argument(..., help="Data file to analyze (CSV or JSON)"),
):
    """Analyze a data file and show its structure, types, and patterns."""
    from ontobuilder.tool.analyzer import DataAnalyzer

    analyzer = DataAnalyzer()
    try:
        profile = analyzer.analyze(file)
    except (FileNotFoundError, ValueError) as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    # Data overview table
    table = Table(title=f"Data Analysis: {Path(profile.file_path).name}")
    table.add_column("Column", style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("Unique", justify="right")
    table.add_column("Nulls", justify="right")
    table.add_column("Notes")

    for col in profile.columns:
        notes = []
        if col.is_id_like:
            notes.append("ID")
        if col.is_foreign_key:
            ref = f" -> {col.referenced_entity}" if col.referenced_entity else ""
            notes.append(f"FK{ref}")
        if col.is_categorical:
            cats = ", ".join(col.categories[:3])
            if len(col.categories) > 3:
                cats += "..."
            notes.append(f"Categorical: {cats}")
        if col.null_rate > 0.3:
            notes.append(f"{col.null_rate:.0%} null")

        table.add_row(
            col.name,
            col.inferred_type,
            str(col.unique_count),
            str(col.null_count),
            " | ".join(notes) if notes else "",
        )

    rprint()
    rprint(table)
    rprint(
        f"\n  {profile.row_count} rows, {len(profile.columns)} columns, "
        f"suggested concept: [bold]{profile.suggested_concept_name}[/bold]"
    )


@tool_app.command("suggest")
def tool_suggest(
    file: str = typer.Argument(..., help="Data file to analyze (CSV or JSON)"),
):
    """Analyze data and show ontology suggestions (concepts, relations, properties)."""
    from ontobuilder.tool.analyzer import DataAnalyzer
    from ontobuilder.tool.suggestions import SuggestionEngine

    analyzer = DataAnalyzer()
    engine = SuggestionEngine()

    try:
        profile = analyzer.analyze(file)
    except (FileNotFoundError, ValueError) as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    suggestions = engine.suggest(profile)

    # Concepts
    rprint(Panel("[bold]Suggested Concepts[/bold]", border_style="green"))
    for cs in suggestions.concepts:
        source_label = {
            "main": "data file", "foreign_key": "foreign key",
            "categorical": "category", "nested": "nested object",
        }.get(cs.source, cs.source)
        rprint(f"  [bold]{cs.name}[/bold] [dim]({source_label})[/dim]")
        rprint(f"    {cs.description}")
        if cs.properties:
            for p in cs.properties:
                req = " *" if p.required else ""
                rprint(f"    - {p.name}: {p.data_type}{req}")

    # Relations
    if suggestions.relations:
        rprint(Panel("[bold]Suggested Relations[/bold]", border_style="blue"))
        for rs in suggestions.relations:
            rprint(
                f"  [bold]{rs.source}[/bold] --[{rs.name}]--> "
                f"[bold]{rs.target}[/bold]  ({rs.cardinality})"
            )
            rprint(f"    [dim]{rs.reason}[/dim]")

    # Notes
    if suggestions.notes:
        rprint(Panel("[bold]Notes[/bold]", border_style="yellow"))
        for note in suggestions.notes:
            rprint(f"  {note}")

    rprint(f"\n  [dim]Total: {suggestions.summary}[/dim]")
    rprint("  [dim]Run 'onto tool build <file>' to build, or 'onto tool build -i <file>' for interactive mode.[/dim]")


@tool_app.command("build")
def tool_build(
    file: str = typer.Argument(..., help="Data file to build ontology from (CSV or JSON)"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactive mode: review and edit each suggestion"
    ),
    output: str = typer.Option(None, "--output", "-o", help="Output file (default: ontology.ttl)"),
    format: str = typer.Option(
        "turtle", "--format", "-f", help="OWL output format: turtle or xml"
    ),
    name: str = typer.Option(None, "--name", "-n", help="Ontology name (default: derived from file)"),
):
    """Build an OWL ontology from a data file. Use -i for interactive mode."""
    from ontobuilder.serialization.yaml_io import save_yaml
    from ontobuilder.cli.helpers import DEFAULT_FILE

    if interactive:
        # Interactive mode
        from ontobuilder.tool.interactive import InteractiveBuilder

        builder = InteractiveBuilder()
        onto = builder.run(file)
        if onto is None:
            raise typer.Exit(1)
    else:
        # Auto mode: accept all suggestions
        from ontobuilder.tool.analyzer import DataAnalyzer
        from ontobuilder.tool.suggestions import SuggestionEngine

        analyzer = DataAnalyzer()
        engine = SuggestionEngine()

        try:
            profile = analyzer.analyze(file)
        except (FileNotFoundError, ValueError) as e:
            rprint(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

        suggestions = engine.suggest(profile)
        onto_name = name or (profile.suggested_concept_name + "Ontology")
        onto = engine.build_ontology(suggestions, onto_name)

        rprint(f"\n[bold green]Built ontology: {onto.name}[/bold green]")
        rprint(f"  Concepts: {len(onto.concepts)}")
        rprint(f"  Relations: {len(onto.relations)}")
        rprint(f"\n{onto.print_tree()}")

    # Override name if provided
    if name:
        onto.name = name

    # Save YAML
    yaml_path = Path(DEFAULT_FILE)
    save_yaml(onto, yaml_path)
    rprint(f"\n[green]Saved YAML: {yaml_path}[/green]")

    # Export OWL
    from ontobuilder.owl.export import save_owl

    if format == "turtle":
        owl_path = Path(output) if output else Path("ontology.ttl")
    else:
        owl_path = Path(output) if output else Path("ontology.owl")
    save_owl(onto, owl_path, fmt=format)
    rprint(f"[green]Saved OWL:  {owl_path}[/green]")

    # Run consistency check
    from ontobuilder.owl.reasoning import OWLReasoner

    reasoner = OWLReasoner(onto)
    result = reasoner.run_inference()
    if result.is_consistent:
        rprint("[green]Consistency check: PASSED[/green]")
    else:
        rprint("[yellow]Consistency issues:[/yellow]")
        for issue in result.consistency_issues:
            rprint(f"  ! {issue}")
