"""MCP server — exposes OntoBuilder as tools for Claude Code and AI assistants.

Run with:
    python -m ontobuilder.mcp_server

Or register in .claude/mcp.json for automatic integration with Claude Code.
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ontobuilder.core.ontology import Ontology
from ontobuilder.serialization.yaml_io import save_yaml, load_yaml

DEFAULT_FILE = "ontology.onto.yaml"

mcp = FastMCP(
    "OntoBuilder",
    instructions=(
        "OntoBuilder helps users create, explore, and export ontologies. "
        "Use these tools to build structured knowledge representations with "
        "concepts (classes), properties, relations, and instances. "
        "Always start by checking the current state with onto_show, then "
        "help the user iteratively build their ontology."
    ),
)


def _find_onto_file() -> Path | None:
    """Find .onto.yaml in current directory."""
    for f in Path(".").iterdir():
        if f.name.endswith(".onto.yaml"):
            return f
    return None


def _load() -> Ontology:
    """Load current ontology or create empty one."""
    path = _find_onto_file()
    if path:
        return load_yaml(path)
    return Ontology("Untitled")


def _save(onto: Ontology) -> Path:
    """Save ontology to disk."""
    path = _find_onto_file() or Path(DEFAULT_FILE)
    save_yaml(onto, path)
    return path


# ── Core tools ──────────────────────────────────────────────────────────────


@mcp.tool()
def onto_init(name: str, description: str = "") -> str:
    """Create a new ontology project. Use this to start building an ontology from scratch."""
    path = _find_onto_file()
    if path:
        return f"Ontology already exists at {path}. Use onto_show to see it."
    onto = Ontology(name, description)
    path = _save(onto)
    return f"Created ontology '{name}' at {path}"


@mcp.tool()
def onto_show() -> str:
    """Show the current ontology state — concepts, relations, instances, and tree."""
    onto = _load()
    parts = [
        f"Ontology: {onto.name}",
        f"Description: {onto.description}" if onto.description else "",
        f"Concepts: {len(onto.concepts)}",
        f"Relations: {len(onto.relations)}",
        f"Instances: {len(onto.instances)}",
        "",
        onto.print_tree(),
    ]
    if onto.relations:
        parts.append("\nRelations:")
        for r in onto.relations.values():
            parts.append(f"  {r.source} --[{r.name}]--> {r.target} ({r.cardinality})")
    return "\n".join(p for p in parts if p is not None)


@mcp.tool()
def onto_add_concept(
    name: str, description: str = "", parent: str | None = None
) -> str:
    """Add a concept (class) to the ontology. Use parent to create a hierarchy."""
    onto = _load()
    try:
        onto.add_concept(name, description=description, parent=parent)
    except Exception as e:
        return f"Error: {e}"
    _save(onto)
    parent_str = f" (child of {parent})" if parent else ""
    return f"Added concept '{name}'{parent_str}"


@mcp.tool()
def onto_add_property(
    concept_name: str,
    property_name: str,
    data_type: str = "string",
    required: bool = False,
) -> str:
    """Add a property to a concept. data_type: string, integer, float, boolean, date, uri."""
    onto = _load()
    try:
        onto.add_property(concept_name, property_name, data_type=data_type, required=required)
    except Exception as e:
        return f"Error: {e}"
    _save(onto)
    return f"Added property '{property_name}' ({data_type}) to concept '{concept_name}'"


@mcp.tool()
def onto_add_relation(
    name: str,
    source: str,
    target: str,
    cardinality: str = "many-to-many",
) -> str:
    """Add a relation between two concepts. cardinality: one-to-one, one-to-many, many-to-many."""
    onto = _load()
    try:
        onto.add_relation(name, source=source, target=target, cardinality=cardinality)
    except Exception as e:
        return f"Error: {e}"
    _save(onto)
    return f"Added relation '{name}': {source} → {target}"


@mcp.tool()
def onto_add_instance(
    name: str,
    concept: str,
    properties: str = "{}",
) -> str:
    """Add an instance of a concept. Properties as JSON string, e.g. '{"age": 5}'."""
    onto = _load()
    try:
        props = json.loads(properties) if properties else {}
        onto.add_instance(name, concept=concept, properties=props)
    except Exception as e:
        return f"Error: {e}"
    _save(onto)
    return f"Added instance '{name}' of concept '{concept}'"


@mcp.tool()
def onto_remove_concept(name: str) -> str:
    """Remove a concept and its related relations/instances."""
    onto = _load()
    try:
        onto.remove_concept(name)
    except Exception as e:
        return f"Error: {e}"
    _save(onto)
    return f"Removed concept '{name}'"


@mcp.tool()
def onto_remove_relation(name: str) -> str:
    """Remove a relation."""
    onto = _load()
    try:
        onto.remove_relation(name)
    except Exception as e:
        return f"Error: {e}"
    _save(onto)
    return f"Removed relation '{name}'"


# ── Export tools ────────────────────────────────────────────────────────────


@mcp.tool()
def onto_export(format: str = "yaml") -> str:
    """Export ontology. format: yaml, json, owl, turtle, jsonld, prompt, schema-card."""
    onto = _load()
    path = _find_onto_file() or Path(DEFAULT_FILE)

    if format == "yaml":
        save_yaml(onto, path)
        return f"Saved YAML to {path}"
    elif format == "json":
        from ontobuilder.serialization.json_io import save_json

        out = path.with_suffix(".json")
        save_json(onto, out)
        return f"Exported JSON to {out}"
    elif format in ("owl", "owl-xml"):
        from ontobuilder.owl.export import save_owl

        out = path.parent / "ontology.owl"
        save_owl(onto, out, fmt="xml")
        return f"Exported OWL-XML to {out}"
    elif format == "turtle":
        from ontobuilder.owl.export import save_owl

        out = path.parent / "ontology.ttl"
        save_owl(onto, out, fmt="turtle")
        return f"Exported Turtle to {out}"
    elif format == "jsonld":
        from ontobuilder.serialization.jsonld_io import save_jsonld

        out = path.parent / "ontology.jsonld"
        save_jsonld(onto, out)
        return f"Exported JSON-LD to {out}"
    elif format == "prompt":
        from ontobuilder.serialization.prompt_io import save_prompt

        out = path.parent / "ontology.prompt.txt"
        save_prompt(onto, out)
        return f"Exported LLM prompt to {out}"
    elif format == "schema-card":
        from ontobuilder.serialization.schemacard_io import save_schema_card

        out = path.parent / "ontology.schema-card.json"
        save_schema_card(onto, out)
        return f"Exported schema card to {out}"
    else:
        return f"Unknown format: {format}. Use: yaml, json, owl, turtle, jsonld, prompt, schema-card"


# ── Analysis tools ──────────────────────────────────────────────────────────


@mcp.tool()
def onto_reason() -> str:
    """Run OWL inference and consistency checks on the ontology."""
    onto = _load()
    from ontobuilder.owl.reasoning import OWLReasoner

    reasoner = OWLReasoner(onto)
    result = reasoner.run_inference()

    parts = [result.summary]
    if result.inferred_subclasses:
        parts.append("\nInferred Subclass Chains:")
        for cls, ancestors in result.inferred_subclasses.items():
            parts.append(f"  {cls} -> {' -> '.join(ancestors)}")
    if result.inherited_properties:
        parts.append("\nInherited Properties:")
        for cls, props in result.inherited_properties.items():
            parts.append(f"  {cls}: {', '.join(props)}")
    if result.instance_types:
        parts.append("\nInstance Classification:")
        for inst, types in result.instance_types.items():
            parts.append(f"  {inst} in {{{', '.join(types)}}}")
    return "\n".join(parts)


@mcp.tool()
def onto_suggest() -> str:
    """Suggest likely next actions based on the current ontology state."""
    onto = _load()
    from ontobuilder.chat.checker import OntologyChat

    checker = OntologyChat(onto)
    suggestions = checker.infer_user_intent(limit=5)
    return "Suggested next actions:\n" + "\n".join(f"  {i}. {s}" for i, s in enumerate(suggestions, 1))


@mcp.tool()
def onto_query(
    query_type: str,
    name: str | None = None,
    target: str | None = None,
) -> str:
    """Query the ontology. query_type: classes, instances, relations, describe, path."""
    onto = _load()
    from ontobuilder.owl.query import StructuredQuery

    engine = StructuredQuery(onto)

    if query_type == "classes":
        result = engine.find_classes(name_contains=name)
    elif query_type == "instances":
        result = engine.find_instances(of_class=name)
    elif query_type == "relations":
        result = engine.find_relations(source=name, target=target)
    elif query_type == "describe" and name:
        result = engine.describe_class(name)
    elif query_type == "path" and name and target:
        result = engine.find_path(name, target)
    else:
        return "Usage: query_type=classes|instances|relations|describe|path, name=..., target=..."

    return str(result.to_table())


@mcp.tool()
def onto_learn(term: str) -> str:
    """Look up an ontology term or concept. E.g. 'concept', 'relation', 'owl', 'rdf'."""
    from ontobuilder.education.glossary import get_definition, GLOSSARY

    definition = get_definition(term)
    if definition:
        return f"{term.title()}: {definition}"
    return f"Term '{term}' not found. Available: {', '.join(sorted(GLOSSARY))}"


# ── Run server ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
