"""Schema Card serialization for ontologies (OntoRAG-compatible format)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ontobuilder.core.ontology import Ontology

# ---------------------------------------------------------------------------
# Type mapping: ontobuilder data types → Schema Card types
# ---------------------------------------------------------------------------

ONTOBUILDER_TO_SCHEMACARD: dict[str, str] = {
    "string": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "date": "date",
}


def export_schema_card(onto: Ontology, namespace: str | None = None) -> str:
    """Export ontology as OntoRAG-compatible Schema Card JSON string.

    Parameters
    ----------
    onto:
        The ontology to export.
    namespace:
        Optional URI namespace.  When omitted, a default is derived from the
        ontology name: ``https://example.org/ontologies/{name}/``.

    Returns
    -------
    str
        A JSON string conforming to the Schema Card format.
    """
    if namespace is None:
        safe_name = onto.name.replace(" ", "")
        namespace = f"https://example.org/ontologies/{safe_name}/"

    version = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    warnings: list[str] = []

    # -- classes --
    classes: list[dict] = []
    for concept in onto.concepts.values():
        if not concept.description:
            warnings.append(f"Concept '{concept.name}' has no description")
        classes.append(
            {
                "name": concept.name,
                "description": concept.description or "",
                "origin": "defined",
            }
        )

    # -- datatype_properties (flattened from all concepts) --
    datatype_properties: list[dict] = []
    for concept in onto.concepts.values():
        for prop in concept.properties:
            sc_range = ONTOBUILDER_TO_SCHEMACARD.get(prop.data_type, prop.data_type)
            datatype_properties.append(
                {
                    "name": prop.name,
                    "domain": concept.name,
                    "range": sc_range,
                    "description": "",
                    "origin": "defined",
                }
            )

    # -- object_properties (from relations) --
    object_properties: list[dict] = []
    for relation in onto.relations.values():
        object_properties.append(
            {
                "name": relation.name,
                "domain": relation.source,
                "range": relation.target,
                "description": "",
                "origin": "defined",
            }
        )

    card: dict = {
        "version": version,
        "namespace": namespace,
        "classes": classes,
        "datatype_properties": datatype_properties,
        "object_properties": object_properties,
        "events": [],
        "aliases": [],
        "warnings": warnings,
    }

    return json.dumps(card, indent=2, ensure_ascii=False)


def save_schema_card(onto: Ontology, path: str | Path, **kwargs) -> Path:
    """Save Schema Card export to file.

    Parameters
    ----------
    onto:
        The ontology to export.
    path:
        Destination file path.
    **kwargs:
        Additional keyword arguments forwarded to :func:`export_schema_card`
        (e.g. ``namespace``).

    Returns
    -------
    Path
        The resolved path of the written file.
    """
    path = Path(path)
    content = export_schema_card(onto, **kwargs)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
