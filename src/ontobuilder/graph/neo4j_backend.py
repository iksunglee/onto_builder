"""Neo4j export backend."""

from __future__ import annotations

from typing import Any

from ontobuilder.core.ontology import Ontology


def export_to_neo4j(onto: Ontology, uri: str, auth: tuple[str, str]) -> None:
    """Export an ontology to a Neo4j database.

    Args:
        onto: The ontology to export.
        uri: Neo4j connection URI (e.g., "bolt://localhost:7687").
        auth: Tuple of (username, password).
    """
    try:
        from neo4j import GraphDatabase
    except ImportError:
        raise ImportError(
            "Neo4j export requires the neo4j driver. "
            "Install with: pip install ontobuilder[neo4j]"
        )

    driver = GraphDatabase.driver(uri, auth=auth)

    with driver.session() as session:
        # Create concept nodes
        for concept in onto.concepts.values():
            props: dict[str, Any] = {
                "name": concept.name,
                "description": concept.description,
            }
            session.run(
                "MERGE (c:Concept {name: $name}) SET c.description = $description",
                **props,
            )

            # Create is-a edges
            if concept.parent:
                session.run(
                    "MATCH (child:Concept {name: $child}), (parent:Concept {name: $parent}) "
                    "MERGE (child)-[:IS_A]->(parent)",
                    child=concept.name,
                    parent=concept.parent,
                )

        # Create relation edges
        for rel in onto.relations.values():
            session.run(
                "MATCH (s:Concept {name: $source}), (t:Concept {name: $target}) "
                "MERGE (s)-[:RELATION {name: $name, cardinality: $cardinality}]->(t)",
                source=rel.source,
                target=rel.target,
                name=rel.name,
                cardinality=rel.cardinality,
            )

        # Create instance nodes
        for inst in onto.instances.values():
            session.run(
                "MERGE (i:Instance {name: $name}) SET i += $props "
                "WITH i "
                "MATCH (c:Concept {name: $concept}) "
                "MERGE (i)-[:INSTANCE_OF]->(c)",
                name=inst.name,
                concept=inst.concept,
                props=inst.properties,
            )

    driver.close()


def generate_cypher(onto: Ontology) -> str:
    """Generate Cypher statements for the ontology (for manual import)."""
    lines: list[str] = []

    for concept in onto.concepts.values():
        desc = concept.description.replace("'", "\\'") if concept.description else ""
        lines.append(
            f"MERGE (:{concept.name}:Concept {{name: '{concept.name}', description: '{desc}'}});"
        )

    for concept in onto.concepts.values():
        if concept.parent:
            lines.append(
                f"MATCH (c:Concept {{name: '{concept.name}'}}), "
                f"(p:Concept {{name: '{concept.parent}'}}) "
                f"MERGE (c)-[:IS_A]->(p);"
            )

    for rel in onto.relations.values():
        lines.append(
            f"MATCH (s:Concept {{name: '{rel.source}'}}), "
            f"(t:Concept {{name: '{rel.target}'}}) "
            f"MERGE (s)-[:RELATION {{name: '{rel.name}'}}]->(t);"
        )

    return "\n".join(lines)
