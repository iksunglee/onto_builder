"""Heuristic data analyzer - understands user data without LLM."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------- data profiles ----------

@dataclass
class ColumnProfile:
    """Statistical profile of a single data column."""

    name: str
    inferred_type: str  # string, int, float, bool, date
    sample_values: list[str] = field(default_factory=list)
    unique_count: int = 0
    null_count: int = 0
    total_count: int = 0
    is_id_like: bool = False
    is_foreign_key: bool = False
    is_categorical: bool = False
    categories: list[str] = field(default_factory=list)
    referenced_entity: str | None = None  # e.g. "customer" from "customer_id"

    @property
    def null_rate(self) -> float:
        return self.null_count / self.total_count if self.total_count else 0.0

    @property
    def uniqueness_ratio(self) -> float:
        return self.unique_count / self.total_count if self.total_count else 0.0


@dataclass
class CleaningSuggestion:
    """A data cleaning suggestion for a specific column."""

    column: str
    issue: str       # "delimited_values", "high_cardinality_entity", "inconsistent_casing", etc.
    description: str  # human-readable explanation
    suggestion: str   # what the user should do
    sample: str       # example value demonstrating the issue


@dataclass
class DataProfile:
    """Complete profile of a data file."""

    file_path: str
    file_type: str  # csv, json
    row_count: int
    columns: list[ColumnProfile]
    suggested_concept_name: str
    nested_objects: list[dict] = field(default_factory=list)  # for JSON
    cleaning_suggestions: list[CleaningSuggestion] = field(default_factory=list)

    @property
    def id_columns(self) -> list[ColumnProfile]:
        return [c for c in self.columns if c.is_id_like]

    @property
    def fk_columns(self) -> list[ColumnProfile]:
        return [c for c in self.columns if c.is_foreign_key]

    @property
    def categorical_columns(self) -> list[ColumnProfile]:
        return [c for c in self.columns if c.is_categorical]

    @property
    def property_columns(self) -> list[ColumnProfile]:
        """Columns suitable as ontology properties (not IDs or FKs)."""
        return [c for c in self.columns if not c.is_id_like and not c.is_foreign_key]


# ---------- analyzer ----------

_ID_SUFFIXES = ("_id", "_key", "_ref", "_code", "_pk", "_fk")
_ID_PATTERNS = re.compile(r"^(id|pk|key)$", re.IGNORECASE)

_DATE_PATTERNS = [
    re.compile(r"^\d{4}-\d{2}-\d{2}"),              # 2024-01-15
    re.compile(r"^\d{2}/\d{2}/\d{4}"),              # 01/15/2024
    re.compile(r"^\d{2}-\d{2}-\d{4}"),              # 15-01-2024
    re.compile(r"^\d{4}/\d{2}/\d{2}"),              # 2024/01/15
]

_BOOL_TRUE = {"true", "yes", "1", "t", "y"}
_BOOL_FALSE = {"false", "no", "0", "f", "n"}
_BOOL_VALUES = _BOOL_TRUE | _BOOL_FALSE

_CATEGORICAL_MAX_UNIQUE = 30
_CATEGORICAL_MIN_ROWS_RATIO = 0.5  # at most 50% unique → categorical


class DataAnalyzer:
    """Analyze data files to understand structure and suggest ontology elements."""

    def analyze(self, file_path: str) -> DataProfile:
        """Analyze a data file and return a DataProfile."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()
        if suffix == ".csv":
            return self._analyze_csv(path)
        elif suffix == ".json":
            return self._analyze_json(path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}. Use CSV or JSON.")

    # ---- CSV ----

    def _analyze_csv(self, path: Path) -> DataProfile:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError(f"CSV has no headers: {path}")
            headers = list(reader.fieldnames)
            rows = list(reader)

        columns_data: dict[str, list[str]] = {h: [] for h in headers}
        for row in rows:
            for h in headers:
                columns_data[h].append(row.get(h, ""))

        columns = [self._profile_column(h, columns_data[h]) for h in headers]
        concept_name = self._concept_name_from_file(path)
        self._detect_ids_and_fks(columns, concept_name)
        cleaning = self._detect_cleaning_issues(columns, columns_data)

        return DataProfile(
            file_path=str(path),
            file_type="csv",
            row_count=len(rows),
            columns=columns,
            suggested_concept_name=concept_name,
            cleaning_suggestions=cleaning,
        )

    # ---- JSON ----

    def _analyze_json(self, path: Path) -> DataProfile:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        # Handle both array-of-objects and single object
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            # Look for the first array value
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    records = v
                    break
            else:
                records = [data]
        else:
            raise ValueError("JSON must be an array of objects or an object with arrays.")

        if not records or not isinstance(records[0], dict):
            raise ValueError("JSON records must be objects with keys.")

        headers = list(records[0].keys())
        columns_data: dict[str, list[str]] = {h: [] for h in headers}
        nested: list[dict] = []

        for rec in records:
            for h in headers:
                val = rec.get(h, "")
                if isinstance(val, dict):
                    nested.append({"parent_key": h, "keys": list(val.keys())})
                    columns_data[h].append(json.dumps(val))
                elif isinstance(val, list):
                    nested.append({"parent_key": h, "is_array": True, "sample": val[:3]})
                    columns_data[h].append(json.dumps(val))
                else:
                    columns_data[h].append(str(val) if val is not None else "")

        columns = [self._profile_column(h, columns_data[h]) for h in headers]
        concept_name = self._concept_name_from_file(path)
        self._detect_ids_and_fks(columns, concept_name)
        cleaning = self._detect_cleaning_issues(columns, columns_data)

        # Deduplicate nested objects
        seen = set()
        unique_nested = []
        for n in nested:
            key = n["parent_key"]
            if key not in seen:
                seen.add(key)
                unique_nested.append(n)

        return DataProfile(
            file_path=str(path),
            file_type="json",
            row_count=len(records),
            columns=columns,
            suggested_concept_name=concept_name,
            nested_objects=unique_nested,
            cleaning_suggestions=cleaning,
        )

    # ---- column profiling ----

    def _profile_column(self, name: str, values: list[str]) -> ColumnProfile:
        non_null = [v for v in values if v.strip()]
        null_count = len(values) - len(non_null)
        unique = set(non_null)
        unique_count = len(unique)
        total = len(values)

        inferred = self._infer_type(non_null)

        # Categorical detection
        is_categorical = False
        categories: list[str] = []
        if (
            inferred == "string"
            and 1 < unique_count <= _CATEGORICAL_MAX_UNIQUE
            and total > 0
            and (unique_count / total) <= _CATEGORICAL_MIN_ROWS_RATIO
        ):
            is_categorical = True
            categories = sorted(unique)

        # Sample values (up to 5 unique)
        samples = list(unique)[:5]

        return ColumnProfile(
            name=name,
            inferred_type=inferred,
            sample_values=samples,
            unique_count=unique_count,
            null_count=null_count,
            total_count=total,
            is_categorical=is_categorical,
            categories=categories,
        )

    def _infer_type(self, values: list[str]) -> str:
        """Infer the data type from a list of non-null string values."""
        if not values:
            return "string"

        sample = values[:200]  # check up to 200 values

        # Check bool first (most specific)
        if all(v.strip().lower() in _BOOL_VALUES for v in sample):
            return "bool"

        # Check int
        int_count = 0
        for v in sample:
            try:
                int(v.strip())
                int_count += 1
            except ValueError:
                break
        if int_count == len(sample):
            return "int"

        # Check float
        float_count = 0
        for v in sample:
            try:
                float(v.strip())
                float_count += 1
            except ValueError:
                break
        if float_count == len(sample):
            return "float"

        # Check date
        date_count = sum(1 for v in sample if any(p.match(v.strip()) for p in _DATE_PATTERNS))
        if date_count >= len(sample) * 0.8:
            return "date"

        return "string"

    # ---- ID / FK detection ----

    def _detect_ids_and_fks(self, columns: list[ColumnProfile], concept_name: str) -> None:
        """Mark columns as primary ID or foreign key references."""
        lower_concept = concept_name.lower()

        for col in columns:
            name_lower = col.name.lower().strip()

            # Primary ID: "id", "pk", or "<concept>_id"
            if (
                _ID_PATTERNS.match(name_lower)
                or name_lower == f"{lower_concept}_id"
                or name_lower == f"{lower_concept}id"
            ):
                col.is_id_like = True
                continue

            # Foreign key: ends with _id, _key, _ref, etc.
            for suffix in _ID_SUFFIXES:
                if name_lower.endswith(suffix):
                    col.is_foreign_key = True
                    # Extract entity name: "customer_id" → "Customer"
                    entity = name_lower[: -len(suffix)]
                    if entity:
                        col.referenced_entity = _to_concept_name(entity)
                    break

    # ---- cleaning suggestions ----

    def _detect_cleaning_issues(
        self,
        columns: list[ColumnProfile],
        columns_data: dict[str, list[str]],
    ) -> list[CleaningSuggestion]:
        """Detect data quality issues and suggest cleaning actions."""
        suggestions: list[CleaningSuggestion] = []

        for col in columns:
            values = columns_data.get(col.name, [])
            non_null = [v for v in values if v.strip()]
            if not non_null:
                continue

            sample = non_null[:100]

            # 1. Delimited values -- columns with comma/semicolon/pipe-separated lists
            if col.inferred_type == "string" and not col.is_id_like and not col.is_foreign_key:
                delimited = self._check_delimited(sample)
                if delimited:
                    sep, example = delimited
                    suggestions.append(CleaningSuggestion(
                        column=col.name,
                        issue="delimited_values",
                        description=(
                            f"Contains '{sep}'-separated lists in {col.name}"
                        ),
                        suggestion=(
                            f"Split '{col.name}' into separate entities/nodes -- "
                            f"each value could be its own concept or instance"
                        ),
                        sample=example,
                    ))

            # 2. Inconsistent casing
            if col.inferred_type == "string" and col.unique_count > 1:
                casing_issue = self._check_casing(sample)
                if casing_issue:
                    suggestions.append(CleaningSuggestion(
                        column=col.name,
                        issue="inconsistent_casing",
                        description=f"Inconsistent casing in '{col.name}'",
                        suggestion=(
                            f"Normalize casing -- same value appears as: {casing_issue}"
                        ),
                        sample=casing_issue,
                    ))

            # 3. High-cardinality entity candidates
            if (
                col.inferred_type == "string"
                and not col.is_id_like
                and not col.is_foreign_key
                and not col.is_categorical
                and col.unique_count > 20
                and 0.1 < col.uniqueness_ratio < 0.9
            ):
                suggestions.append(CleaningSuggestion(
                    column=col.name,
                    issue="high_cardinality_entity",
                    description=(
                        f"'{col.name}' has {col.unique_count} unique values "
                        f"({col.uniqueness_ratio:.0%} unique)"
                    ),
                    suggestion=(
                        f"Consider making '{col.name}' its own concept/node -- "
                        f"it may represent a separate entity type"
                    ),
                    sample=", ".join(col.sample_values[:3]),
                ))

            # 4. Embedded structure (JSON-like, key=value)
            if col.inferred_type == "string":
                embedded = self._check_embedded_structure(sample)
                if embedded:
                    suggestions.append(CleaningSuggestion(
                        column=col.name,
                        issue="embedded_structure",
                        description=f"'{col.name}' contains embedded structured data",
                        suggestion=(
                            f"Break down '{col.name}' into separate properties/columns "
                            f"for each sub-field"
                        ),
                        sample=embedded,
                    ))

            # 5. Nullable columns suggesting optional relationships
            if (
                0.1 < col.null_rate < 0.7
                and col.inferred_type == "string"
                and not col.is_id_like
                and col.unique_count > 5
            ):
                suggestions.append(CleaningSuggestion(
                    column=col.name,
                    issue="sparse_optional",
                    description=(
                        f"'{col.name}' is {col.null_rate:.0%} empty -- "
                        f"may represent an optional relationship"
                    ),
                    suggestion=(
                        f"Model '{col.name}' as an optional relation rather than "
                        f"a required property"
                    ),
                    sample=f"{col.null_count}/{col.total_count} rows empty",
                ))

            # 6. Whitespace issues
            if col.inferred_type == "string":
                ws_count = sum(1 for v in sample if v != v.strip())
                if ws_count > len(sample) * 0.1:
                    suggestions.append(CleaningSuggestion(
                        column=col.name,
                        issue="whitespace",
                        description=f"'{col.name}' has leading/trailing whitespace",
                        suggestion=f"Trim whitespace in '{col.name}' before importing",
                        sample=f"{ws_count} of {len(sample)} sampled values have extra spaces",
                    ))

        return suggestions

    def _check_delimited(self, values: list[str]) -> tuple[str, str] | None:
        """Check if values contain delimited lists. Returns (separator, example) or None."""
        for sep in [",", ";", "|"]:
            count = 0
            example = ""
            for v in values:
                parts = [p.strip() for p in v.split(sep) if p.strip()]
                if len(parts) >= 2 and all(len(p) < 50 for p in parts):
                    count += 1
                    if not example:
                        example = v
            # At least 30% of values have this pattern
            if count >= len(values) * 0.3:
                return sep, example
        return None

    def _check_casing(self, values: list[str]) -> str | None:
        """Check for inconsistent casing. Returns example pair or None."""
        lower_map: dict[str, list[str]] = {}
        for v in values:
            key = v.strip().lower()
            if key not in lower_map:
                lower_map[key] = []
            if v.strip() not in lower_map[key]:
                lower_map[key].append(v.strip())
        for _key, variants in lower_map.items():
            if len(variants) > 1:
                return " vs ".join(f"'{v}'" for v in variants[:3])
        return None

    def _check_embedded_structure(self, values: list[str]) -> str | None:
        """Check for JSON-like or key=value embedded structure."""
        json_count = 0
        kv_count = 0
        example = ""
        for v in values:
            stripped = v.strip()
            if (stripped.startswith("{") and stripped.endswith("}")) or \
               (stripped.startswith("[") and stripped.endswith("]")):
                json_count += 1
                if not example:
                    example = stripped[:80]
            elif "=" in stripped and not stripped.startswith("http"):
                parts = stripped.split("=")
                if len(parts) >= 2 and len(parts[0]) < 30:
                    kv_count += 1
                    if not example:
                        example = stripped[:80]
        if json_count >= len(values) * 0.3:
            return example
        if kv_count >= len(values) * 0.3:
            return example
        return None

    # ---- helpers ----

    def _concept_name_from_file(self, path: Path) -> str:
        """Derive a concept name from filename. 'orders.csv' → 'Order'."""
        stem = path.stem.lower()
        # Remove common prefixes/suffixes
        for remove in ("data_", "raw_", "export_", "_data", "_export", "_raw", "_sample"):
            stem = stem.replace(remove, "")
        return _to_concept_name(stem)


def _to_concept_name(raw: str) -> str:
    """Convert a raw string to PascalCase concept name. 'order_items' → 'OrderItem'."""
    # Handle snake_case and kebab-case
    parts = [p for p in re.split(r"[_\-\s]+", raw.strip()) if p]
    if not parts:
        return "Thing"
    # Singularize naive: remove trailing 's' if word > 3 chars
    # Don't strip 's' from words ending in 'ss', 'us', 'is' (status, address, analysis)
    _KEEP_S = ("ss", "us", "is")
    result = []
    for p in parts:
        word = p.capitalize()
        if len(word) > 3 and word.endswith("s") and not any(word.endswith(x) for x in _KEEP_S):
            word = word[:-1]
        result.append(word)
    return "".join(result)
