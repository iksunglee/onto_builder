"""OWL/RDF export using rdflib — produces standards-compliant OWL ontologies."""

from __future__ import annotations

import re
from pathlib import Path

from rdflib import (
    BNode,
    Graph,
    Literal,
    Namespace,
    URIRef,
)
from rdflib.namespace import OWL, RDF, RDFS, XSD

from ontobuilder.core.ontology import Ontology

# Mapping from ontobuilder data types to XSD URIs
_XSD_MAP = {
    "string": XSD.string,
    "int": XSD.integer,
    "float": URIRef("http://www.w3.org/2001/XMLSchema#float"),
    "bool": XSD.boolean,
    "date": XSD.date,
}

# OWL cardinality mapping
_CARD_MAP = {
    "one-to-one": (1, 1),
    "one-to-many": (1, None),
    "many-to-one": (None, 1),
    "many-to-many": (None, None),
}


def _slugify(name: str) -> str:
    slug = name.lower().replace(" ", "_")
    return re.sub(r"[^a-z0-9_]", "", slug)


def to_rdflib_graph(onto: Ontology, namespace: str | None = None) -> Graph:
    """Convert an Ontology to an rdflib Graph with proper OWL structure.

    Args:
        onto: The ontology to convert.
        namespace: Base namespace URI. Defaults to
            ``https://example.org/ontologies/{name}/``.

    Returns:
        An rdflib Graph with OWL classes, properties, and individuals.
    """
    slug = _slugify(onto.name)
    if namespace is None:
        namespace = f"https://example.org/ontologies/{slug}/"

    ns = Namespace(namespace)
    g = Graph()
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("onto", ns)

    # Ontology declaration
    onto_uri = URIRef(namespace.rstrip("/"))
    g.add((onto_uri, RDF.type, OWL.Ontology))
    g.add((onto_uri, RDFS.label, Literal(onto.name)))
    if onto.description:
        g.add((onto_uri, RDFS.comment, Literal(onto.description)))

    # Classes (concepts)
    for concept in onto.concepts.values():
        cls_uri = ns[_slugify(concept.name)]
        g.add((cls_uri, RDF.type, OWL.Class))
        g.add((cls_uri, RDFS.label, Literal(concept.name)))
        if concept.description:
            g.add((cls_uri, RDFS.comment, Literal(concept.description)))
        if concept.parent:
            parent_uri = ns[_slugify(concept.parent)]
            g.add((cls_uri, RDFS.subClassOf, parent_uri))
        else:
            # Top-level classes are subclass of owl:Thing
            g.add((cls_uri, RDFS.subClassOf, OWL.Thing))

        # Datatype properties
        for prop in concept.properties:
            prop_uri = ns[_slugify(f"{concept.name}_{prop.name}")]
            g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
            g.add((prop_uri, RDFS.label, Literal(prop.name)))
            g.add((prop_uri, RDFS.domain, cls_uri))
            xsd_type = _XSD_MAP.get(prop.data_type, XSD.string)
            g.add((prop_uri, RDFS.range, xsd_type))

            # Required properties get min cardinality 1 restriction
            if prop.required:
                restriction = BNode()
                g.add((restriction, RDF.type, OWL.Restriction))
                g.add((restriction, OWL.onProperty, prop_uri))
                g.add(
                    (restriction, OWL.minCardinality, Literal(1, datatype=XSD.nonNegativeInteger))
                )
                g.add((cls_uri, RDFS.subClassOf, restriction))

    # Object properties (relations)
    for relation in onto.relations.values():
        rel_uri = ns[_slugify(relation.name)]
        g.add((rel_uri, RDF.type, OWL.ObjectProperty))
        g.add((rel_uri, RDFS.label, Literal(relation.name)))
        g.add((rel_uri, RDFS.domain, ns[_slugify(relation.source)]))
        g.add((rel_uri, RDFS.range, ns[_slugify(relation.target)]))

        # Cardinality restrictions on the source class
        min_card, max_card = _CARD_MAP.get(relation.cardinality, (None, None))
        if min_card is not None or max_card is not None:
            source_uri = ns[_slugify(relation.source)]
            if min_card is not None:
                restriction = BNode()
                g.add((restriction, RDF.type, OWL.Restriction))
                g.add((restriction, OWL.onProperty, rel_uri))
                g.add(
                    (
                        restriction,
                        OWL.minCardinality,
                        Literal(min_card, datatype=XSD.nonNegativeInteger),
                    )
                )
                g.add((source_uri, RDFS.subClassOf, restriction))
            if max_card is not None:
                restriction = BNode()
                g.add((restriction, RDF.type, OWL.Restriction))
                g.add((restriction, OWL.onProperty, rel_uri))
                g.add(
                    (
                        restriction,
                        OWL.maxCardinality,
                        Literal(max_card, datatype=XSD.nonNegativeInteger),
                    )
                )
                g.add((source_uri, RDFS.subClassOf, restriction))

    # Individuals (instances)
    for inst in onto.instances.values():
        inst_uri = ns[_slugify(inst.name)]
        cls_uri = ns[_slugify(inst.concept)]
        g.add((inst_uri, RDF.type, OWL.NamedIndividual))
        g.add((inst_uri, RDF.type, cls_uri))
        g.add((inst_uri, RDFS.label, Literal(inst.name)))

        # Instance properties
        for prop_name, value in inst.properties.items():
            prop_uri = ns[_slugify(f"{inst.concept}_{prop_name}")]
            if isinstance(value, bool):
                g.add((inst_uri, prop_uri, Literal(value, datatype=XSD.boolean)))
            elif isinstance(value, int):
                g.add((inst_uri, prop_uri, Literal(value, datatype=XSD.integer)))
            elif isinstance(value, float):
                g.add(
                    (
                        inst_uri,
                        prop_uri,
                        Literal(value, datatype=URIRef("http://www.w3.org/2001/XMLSchema#float")),
                    )
                )
            else:
                g.add((inst_uri, prop_uri, Literal(str(value))))

    return g


def export_owl_xml(onto: Ontology, namespace: str | None = None) -> str:
    """Export ontology as OWL/RDF-XML string."""
    g = to_rdflib_graph(onto, namespace)
    return g.serialize(format="xml")


def export_turtle(onto: Ontology, namespace: str | None = None) -> str:
    """Export ontology as Turtle format string."""
    g = to_rdflib_graph(onto, namespace)
    return g.serialize(format="turtle")


def save_owl(onto: Ontology, path: str | Path, fmt: str = "xml", **kwargs) -> Path:
    """Save OWL export to file.

    Args:
        onto: The ontology to export.
        path: Destination file path.
        fmt: Format — ``"xml"`` for RDF/XML or ``"turtle"`` for Turtle.
        **kwargs: Forwarded to :func:`to_rdflib_graph`.

    Returns:
        The resolved path of the written file.
    """
    path = Path(path)
    g = to_rdflib_graph(onto, **kwargs)
    g.serialize(destination=str(path), format=fmt)
    return path
