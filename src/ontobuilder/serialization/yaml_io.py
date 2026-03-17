"""YAML serialization for ontologies."""

from __future__ import annotations

from pathlib import Path

import yaml

from ontobuilder.core.ontology import Ontology


def save_yaml(onto: Ontology, path: str | Path) -> Path:
    """Save an ontology to a .onto.yaml file."""
    path = Path(path)
    data = onto.to_dict()
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return path


def load_yaml(path: str | Path) -> Ontology:
    """Load an ontology from a .onto.yaml file."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Ontology.from_dict(data)
