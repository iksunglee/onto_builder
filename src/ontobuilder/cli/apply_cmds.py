"""CLI commands for applying ontology to LLM solutions."""

import typer

apply_app = typer.Typer(no_args_is_help=True)


@apply_app.command()
def jsonschema(
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
    scenario: str = typer.Option(
        None, "--scenario", "-s", help="Scenario name from .onto.yaml"
    ),
    wrapper: str = typer.Option(
        None, "--format", "-f", help="Wrapper format: openai, anthropic"
    ),
    split: bool = typer.Option(
        False, "--split", help="One file per concept in output directory"
    ),
):
    """Generate JSON Schema from ontology concepts."""
    import json
    from pathlib import Path

    from ontobuilder.cli.helpers import load_current_ontology
    from ontobuilder.serialization.jsonschema_io import (
        export_jsonschema,
        export_jsonschema_scenario,
        save_jsonschema,
    )

    onto, path = load_current_ontology()

    if scenario:
        if scenario not in onto.scenarios:
            available = ", ".join(onto.scenarios.keys()) or "none"
            typer.echo(
                f"Scenario '{scenario}' not found. Available: {available}"
            )
            raise typer.Exit(1)
        data = export_jsonschema_scenario(onto, scenario, wrapper=wrapper)
    else:
        data = export_jsonschema(onto)

    if split and not scenario:
        out_dir = Path(output) if output else path.parent / "schemas"
        out_dir.mkdir(exist_ok=True)
        defs = data.get("$defs", {})
        for concept_name, concept_schema in defs.items():
            concept_file = out_dir / f"{concept_name}.json"
            with open(concept_file, "w", encoding="utf-8") as f:
                json.dump(concept_schema, f, indent=2, ensure_ascii=False)
            typer.echo(f"  -> {concept_file}")
        typer.echo(f"Wrote {len(defs)} schema files to {out_dir}")
        return

    if output:
        save_jsonschema(onto, output, scenario=scenario, wrapper=wrapper)
        typer.echo(f"JSON Schema written to {output}")
    else:
        typer.echo(json.dumps(data, indent=2, ensure_ascii=False))


@apply_app.command()
def prompt(
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
    sections: str = typer.Option(
        None,
        "--sections",
        help="Comma-separated: overview,concepts,rules,constraints,values,scenarios",
    ),
    with_queries: bool = typer.Option(
        False, "--with-queries", help="Include query logic section"
    ),
    audience: str = typer.Option(
        "developer", "--audience", help="developer or enduser"
    ),
    max_tokens: int = typer.Option(
        None, "--max-tokens", help="Approximate token budget"
    ),
):
    """Generate an enhanced LLM system prompt from ontology."""
    from ontobuilder.cli.helpers import load_current_ontology
    from ontobuilder.serialization.prompt_enhanced import (
        export_enhanced_prompt,
        save_enhanced_prompt,
    )

    onto, _path = load_current_ontology()
    section_list = sections.split(",") if sections else None

    if output:
        save_enhanced_prompt(
            onto,
            output,
            sections=section_list,
            with_queries=with_queries,
            audience=audience,
            max_tokens=max_tokens,
        )
        typer.echo(f"Enhanced prompt written to {output}")
    else:
        text = export_enhanced_prompt(
            onto,
            sections=section_list,
            with_queries=with_queries,
            audience=audience,
            max_tokens=max_tokens,
        )
        typer.echo(text)


@apply_app.command()
def fewshot(
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
    scenario: str = typer.Option(
        None, "--scenario", "-s", help="Filter to scenario"
    ),
    include_traces: bool = typer.Option(
        False, "--include-traces", help="Include query traces"
    ),
    format: str = typer.Option(
        "examples", "--format", "-f", help="examples or messages"
    ),
):
    """Generate few-shot examples from ontology instances."""
    import json

    from ontobuilder.cli.helpers import load_current_ontology
    from ontobuilder.serialization.fewshot_io import export_fewshot, save_fewshot

    onto, _path = load_current_ontology()

    if output:
        save_fewshot(
            onto,
            output,
            scenario=scenario,
            include_traces=include_traces,
            format=format,
        )
        typer.echo(f"Few-shot examples written to {output}")
    else:
        data = export_fewshot(
            onto,
            scenario=scenario,
            include_traces=include_traces,
            format=format,
        )
        typer.echo(json.dumps(data, indent=2, ensure_ascii=False))
