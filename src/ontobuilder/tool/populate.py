"""Populate an ontology with instances from data rows."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from ontobuilder.core.ontology import Ontology
from ontobuilder.tool.analyzer import DataAnalyzer, DataProfile


def populate_ontology(
    onto: Ontology,
    file_path: str | Path,
    *,
    max_rows: int = 200,
) -> dict[str, int]:
    """Read data and create instances for each concept in the ontology.

    Returns a summary dict: {"instances": N, "skipped": M}.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        rows = _read_csv_rows(path, max_rows)
    elif suffix == ".json":
        rows = _read_json_rows(path, max_rows)
    else:
        return {"instances": 0, "skipped": 0}

    if not rows:
        return {"instances": 0, "skipped": 0}

    # Analyze the data to understand column roles
    analyzer = DataAnalyzer()
    profile = analyzer.analyze(str(path))

    # Build column → concept mapping
    col_map = _build_column_map(onto, profile)

    added = 0
    skipped = 0

    # Track unique values for FK/categorical concepts to avoid duplicates
    seen_instances: dict[str, set[str]] = {}

    for i, row in enumerate(rows):
        # 1. Create instances for categorical and FK concepts (unique values only)
        for col_name, (concept_name, prop_name) in col_map.items():
            if concept_name == profile.suggested_concept_name:
                continue  # main concept handled below
            val = str(row.get(col_name, "")).strip()
            if not val:
                continue

            # Use the value as instance name
            instance_name = _safe_instance_name(val, concept_name)
            if concept_name not in seen_instances:
                seen_instances[concept_name] = set()
            if instance_name in seen_instances[concept_name]:
                continue
            seen_instances[concept_name].add(instance_name)

            if concept_name in onto.concepts and instance_name not in onto.instances:
                try:
                    onto.add_instance(instance_name, concept=concept_name, properties={})
                    added += 1
                except Exception:
                    skipped += 1

        # 2. Create main concept instance from the row
        main_concept = profile.suggested_concept_name
        if main_concept not in onto.concepts:
            continue

        # Try to find a good instance name from ID columns or row index
        instance_name = _row_instance_name(row, profile, i)
        if instance_name in onto.instances:
            skipped += 1
            continue

        # Collect properties that belong to the main concept
        props = {}
        for col_name in row:
            if col_name in col_map and col_map[col_name][0] != main_concept:
                continue  # belongs to another concept
            val = row.get(col_name, "")
            if val is None:
                continue
            val_str = str(val).strip()
            if not val_str:
                continue
            # Only add properties that exist on the concept
            concept_obj = onto.concepts.get(main_concept)
            if concept_obj and col_name in {p.name for p in concept_obj.properties}:
                props[col_name] = _coerce_value(val_str)

        try:
            onto.add_instance(instance_name, concept=main_concept, properties=props)
            added += 1
        except Exception:
            skipped += 1

    return {"instances": added, "skipped": skipped}


def _build_column_map(
    onto: Ontology, profile: DataProfile
) -> dict[str, tuple[str, str]]:
    """Map column names to (concept_name, property_name) pairs."""
    col_map: dict[str, tuple[str, str]] = {}

    # Categorical columns → their concept
    from ontobuilder.tool.suggestions import _col_to_concept_name

    for col in profile.categorical_columns:
        concept_name = _col_to_concept_name(col.name)
        if concept_name in onto.concepts:
            col_map[col.name] = (concept_name, col.name)

    # FK columns → their referenced entity
    for col in profile.fk_columns:
        if col.referenced_entity and col.referenced_entity in onto.concepts:
            col_map[col.name] = (col.referenced_entity, col.name)

    return col_map


def _row_instance_name(row: dict, profile: DataProfile, index: int) -> str:
    """Generate an instance name from a data row."""
    # Try ID columns first
    for col in profile.id_columns:
        val = str(row.get(col.name, "")).strip()
        if val:
            return _safe_instance_name(val, profile.suggested_concept_name)

    # Try first FK that looks like a primary key (e.g., order_id for Order)
    concept_lower = profile.suggested_concept_name.lower()
    for col in profile.fk_columns:
        col_lower = col.name.lower()
        if concept_lower in col_lower:
            val = str(row.get(col.name, "")).strip()
            if val:
                return _safe_instance_name(val, profile.suggested_concept_name)

    return f"{profile.suggested_concept_name}_{index + 1}"


def _safe_instance_name(value: str, concept: str) -> str:
    """Create a safe instance name from a value."""
    # Replace spaces and special chars
    name = value.replace(" ", "_").replace("/", "_").replace("\\", "_")
    name = "".join(c for c in name if c.isalnum() or c in "_-.")
    if not name:
        return f"{concept}_unknown"
    # Ensure it starts with a letter
    if not name[0].isalpha():
        name = f"{concept}_{name}"
    return name[:60]  # cap length


def _coerce_value(val: str) -> str | int | float | bool:
    """Try to coerce a string value to its native type."""
    if val.lower() in ("true", "yes", "y"):
        return True
    if val.lower() in ("false", "no", "n"):
        return False
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


def _read_csv_rows(path: Path, max_rows: int) -> list[dict[str, str]]:
    """Read CSV rows as dicts."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            rows.append(dict(row))
    return rows


def _read_json_rows(path: Path, max_rows: int) -> list[dict]:
    """Read JSON rows as dicts."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        records = data[:max_rows]
    elif isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                records = v[:max_rows]
                break
        else:
            records = [data]
    else:
        return []

    return [r for r in records if isinstance(r, dict)]
