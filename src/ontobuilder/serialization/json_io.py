"""JSON serialization for ontologies."""

from __future__ import annotations

import json
from pathlib import Path

from ontobuilder.core.ontology import Ontology


def save_json(onto: Ontology, path: str | Path) -> Path:
    """Save an ontology to a JSON file."""
    path = Path(path)
    data = onto.to_dict()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def load_json(path: str | Path) -> Ontology:
    """Load an ontology from a JSON file."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Ontology.from_dict(data)
