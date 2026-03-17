"""JSON-LD export for ontologies.

Produces JSON-LD for LLM structured grounding (not W3C JSON-LD compliant).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ontobuilder.core.ontology import Ontology

# Mapping from ontobuilder data types to XSD types
ONTOBUILDER_TO_XSD = {
    "string": "xsd:string",
    "int": "xsd:integer",
    "float": "xsd:float",
    "bool": "xsd:boolean",
    "date": "xsd:date",
}


def _slugify(name: str) -> str:
    """Convert name to URI-safe slug: lowercase, spaces→underscores, strip special chars."""
    slug = name.lower().replace(" ", "_")
    return re.sub(r"[^a-z0-9_]", "", slug)


def export_jsonld(onto: Ontology, namespace: str | None = None) -> str:
    """Export ontology as JSON-LD string for LLM structured grounding.

    Args:
        onto: The ontology to export.
        namespace: Optional base namespace URI. Defaults to
            ``https://example.org/ontologies/{slugified_name}/``.

    Returns:
        A JSON-LD string representation of the ontology.
    """
    onto_slug = _slugify(onto.name)
    if namespace is None:
        namespace = f"https://example.org/ontologies/{onto_slug}/"

    context = {
        "@vocab": namespace,
        "owl": "http://www.w3.org/2002/07/owl#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
    }

    graph: list[dict] = []

    # Add owl:Class nodes for each concept
    for concept in onto.concepts.values():
        concept_slug = _slugify(concept.name)
        node: dict = {
            "@id": f"onto:{concept_slug}",
            "@type": "owl:Class",
            "rdfs:label": concept.name,
        }
        if concept.description:
            node["rdfs:comment"] = concept.description
        if concept.parent:
            parent_slug = _slugify(concept.parent)
            node["rdfs:subClassOf"] = {"@id": f"onto:{parent_slug}"}
        graph.append(node)

        # Add owl:DatatypeProperty nodes for each property on this concept
        for prop in concept.properties:
            prop_slug = _slugify(f"{concept.name}_{prop.name}")
            xsd_type = ONTOBUILDER_TO_XSD.get(prop.data_type, "xsd:string")
            prop_node: dict = {
                "@id": f"onto:{prop_slug}",
                "@type": "owl:DatatypeProperty",
                "rdfs:label": prop.name,
                "rdfs:domain": {"@id": f"onto:{concept_slug}"},
                "rdfs:range": {"@id": xsd_type},
            }
            graph.append(prop_node)

    # Add owl:ObjectProperty nodes for each relation
    for relation in onto.relations.values():
        rel_slug = _slugify(relation.name)
        source_slug = _slugify(relation.source)
        target_slug = _slugify(relation.target)
        rel_node: dict = {
            "@id": f"onto:{rel_slug}",
            "@type": "owl:ObjectProperty",
            "rdfs:label": relation.name,
            "rdfs:domain": {"@id": f"onto:{source_slug}"},
            "rdfs:range": {"@id": f"onto:{target_slug}"},
        }
        graph.append(rel_node)

    doc = {
        "@context": context,
        "@id": namespace,
        "@type": "owl:Ontology",
        "rdfs:label": onto.name,
        "@graph": graph,
    }
    if onto.description:
        doc["rdfs:comment"] = onto.description

    return json.dumps(doc, indent=2, ensure_ascii=False)


def save_jsonld(onto: Ontology, path: str | Path, **kwargs) -> Path:
    """Save JSON-LD export to file.

    Args:
        onto: The ontology to export.
        path: Destination file path.
        **kwargs: Additional keyword arguments forwarded to :func:`export_jsonld`.

    Returns:
        The resolved :class:`~pathlib.Path` of the written file.
    """
    path = Path(path)
    content = export_jsonld(onto, **kwargs)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
