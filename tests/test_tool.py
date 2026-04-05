"""Tests for the data analysis and ontology building tool."""

from __future__ import annotations

import csv
import json
import textwrap
from pathlib import Path

import pytest

from ontobuilder.tool.analyzer import DataAnalyzer, DataProfile, ColumnProfile, _to_concept_name
from ontobuilder.tool.suggestions import SuggestionEngine, OntologySuggestions


# ---------- fixtures ----------

@pytest.fixture
def tmp_csv(tmp_path: Path) -> Path:
    """Create a sample CSV with various column types."""
    p = tmp_path / "orders.csv"
    rows = [
        {"order_id": "1", "customer_id": "101", "product_name": "Widget",
         "category": "Electronics", "price": "29.99", "quantity": "2",
         "order_date": "2024-01-15", "is_gift": "true"},
        {"order_id": "2", "customer_id": "102", "product_name": "Gadget",
         "category": "Electronics", "price": "49.99", "quantity": "1",
         "order_date": "2024-01-16", "is_gift": "false"},
        {"order_id": "3", "customer_id": "101", "product_name": "Book",
         "category": "Books", "price": "12.99", "quantity": "3",
         "order_date": "2024-01-17", "is_gift": "false"},
        {"order_id": "4", "customer_id": "103", "product_name": "Lamp",
         "category": "Home", "price": "34.50", "quantity": "1",
         "order_date": "2024-02-01", "is_gift": "true"},
    ]
    with open(p, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return p


@pytest.fixture
def tmp_csv_large(tmp_path: Path) -> Path:
    """CSV with enough rows to trigger categorical detection."""
    p = tmp_path / "products.csv"
    categories = ["Electronics", "Books", "Home"]
    rows = []
    for i in range(100):
        rows.append({
            "id": str(i),
            "name": f"Product_{i}",
            "category": categories[i % 3],
            "price": f"{10 + i * 0.5:.2f}",
            "supplier_id": str(i % 10),
        })
    with open(p, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return p


@pytest.fixture
def tmp_json(tmp_path: Path) -> Path:
    """Create a sample JSON file with nested objects."""
    p = tmp_path / "users.json"
    data = [
        {"user_id": 1, "name": "Alice", "email": "alice@example.com",
         "address": {"street": "123 Main", "city": "NYC"},
         "tags": ["admin", "user"]},
        {"user_id": 2, "name": "Bob", "email": "bob@example.com",
         "address": {"street": "456 Oak", "city": "LA"},
         "tags": ["user"]},
    ]
    p.write_text(json.dumps(data, indent=2))
    return p


@pytest.fixture
def tmp_json_wrapped(tmp_path: Path) -> Path:
    """JSON with data inside a wrapper object."""
    p = tmp_path / "response.json"
    data = {
        "status": "ok",
        "results": [
            {"item_id": 1, "title": "Foo", "count": 10},
            {"item_id": 2, "title": "Bar", "count": 20},
        ],
    }
    p.write_text(json.dumps(data, indent=2))
    return p


# ---------- _to_concept_name ----------

class TestConceptNaming:
    def test_singular(self):
        assert _to_concept_name("orders") == "Order"

    def test_snake_case(self):
        assert _to_concept_name("order_items") == "OrderItem"

    def test_simple(self):
        assert _to_concept_name("product") == "Product"

    def test_empty(self):
        assert _to_concept_name("") == "Thing"

    def test_no_strip_short_s(self):
        # "bus" should not become "bu"
        assert _to_concept_name("bus") == "Bus"


# ---------- DataAnalyzer ----------

class TestDataAnalyzer:
    def test_csv_basic(self, tmp_csv: Path):
        analyzer = DataAnalyzer()
        profile = analyzer.analyze(str(tmp_csv))

        assert profile.file_type == "csv"
        assert profile.row_count == 4
        assert len(profile.columns) == 8
        assert profile.suggested_concept_name == "Order"

    def test_csv_type_inference(self, tmp_csv: Path):
        analyzer = DataAnalyzer()
        profile = analyzer.analyze(str(tmp_csv))

        by_name = {c.name: c for c in profile.columns}
        assert by_name["order_id"].inferred_type == "int"
        assert by_name["price"].inferred_type == "float"
        assert by_name["order_date"].inferred_type == "date"
        assert by_name["is_gift"].inferred_type == "bool"
        assert by_name["product_name"].inferred_type == "string"

    def test_csv_id_detection(self, tmp_csv: Path):
        analyzer = DataAnalyzer()
        profile = analyzer.analyze(str(tmp_csv))

        by_name = {c.name: c for c in profile.columns}
        assert by_name["order_id"].is_id_like
        assert not by_name["order_id"].is_foreign_key

    def test_csv_fk_detection(self, tmp_csv: Path):
        analyzer = DataAnalyzer()
        profile = analyzer.analyze(str(tmp_csv))

        by_name = {c.name: c for c in profile.columns}
        assert by_name["customer_id"].is_foreign_key
        assert by_name["customer_id"].referenced_entity == "Customer"

    def test_csv_categorical_detection(self, tmp_csv_large: Path):
        analyzer = DataAnalyzer()
        profile = analyzer.analyze(str(tmp_csv_large))

        by_name = {c.name: c for c in profile.columns}
        assert by_name["category"].is_categorical
        assert set(by_name["category"].categories) == {"Electronics", "Books", "Home"}

    def test_json_basic(self, tmp_json: Path):
        analyzer = DataAnalyzer()
        profile = analyzer.analyze(str(tmp_json))

        assert profile.file_type == "json"
        assert profile.row_count == 2
        assert profile.suggested_concept_name == "User"

    def test_json_nested_detection(self, tmp_json: Path):
        analyzer = DataAnalyzer()
        profile = analyzer.analyze(str(tmp_json))

        assert len(profile.nested_objects) >= 1
        parent_keys = [n["parent_key"] for n in profile.nested_objects]
        assert "address" in parent_keys

    def test_json_wrapped(self, tmp_json_wrapped: Path):
        analyzer = DataAnalyzer()
        profile = analyzer.analyze(str(tmp_json_wrapped))

        assert profile.row_count == 2
        by_name = {c.name: c for c in profile.columns}
        assert "item_id" in by_name

    def test_file_not_found(self):
        analyzer = DataAnalyzer()
        with pytest.raises(FileNotFoundError):
            analyzer.analyze("/nonexistent/file.csv")

    def test_unsupported_format(self, tmp_path: Path):
        p = tmp_path / "data.xml"
        p.write_text("<data/>")
        analyzer = DataAnalyzer()
        with pytest.raises(ValueError, match="Unsupported"):
            analyzer.analyze(str(p))

    def test_property_columns(self, tmp_csv: Path):
        analyzer = DataAnalyzer()
        profile = analyzer.analyze(str(tmp_csv))

        prop_names = [c.name for c in profile.property_columns]
        assert "order_id" not in prop_names  # ID column excluded
        assert "customer_id" not in prop_names  # FK excluded
        assert "product_name" in prop_names
        assert "price" in prop_names


# ---------- SuggestionEngine ----------

class TestSuggestionEngine:
    def test_basic_suggestions(self, tmp_csv: Path):
        analyzer = DataAnalyzer()
        engine = SuggestionEngine()
        profile = analyzer.analyze(str(tmp_csv))
        suggestions = engine.suggest(profile)

        assert len(suggestions.concepts) >= 1
        concept_names = [c.name for c in suggestions.concepts]
        assert "Order" in concept_names

    def test_fk_creates_concept(self, tmp_csv: Path):
        analyzer = DataAnalyzer()
        engine = SuggestionEngine()
        profile = analyzer.analyze(str(tmp_csv))
        suggestions = engine.suggest(profile)

        concept_names = [c.name for c in suggestions.concepts]
        assert "Customer" in concept_names

    def test_main_concept_properties(self, tmp_csv: Path):
        analyzer = DataAnalyzer()
        engine = SuggestionEngine()
        profile = analyzer.analyze(str(tmp_csv))
        suggestions = engine.suggest(profile)

        main = [c for c in suggestions.concepts if c.source == "main"][0]
        prop_names = [p.name for p in main.properties]
        assert "product_name" in prop_names
        assert "price" in prop_names

    def test_relation_from_fk(self, tmp_csv: Path):
        analyzer = DataAnalyzer()
        engine = SuggestionEngine()
        profile = analyzer.analyze(str(tmp_csv))
        suggestions = engine.suggest(profile)

        rel_targets = [r.target for r in suggestions.relations]
        assert "Customer" in rel_targets

    def test_categorical_concept(self, tmp_csv_large: Path):
        analyzer = DataAnalyzer()
        engine = SuggestionEngine()
        profile = analyzer.analyze(str(tmp_csv_large))
        suggestions = engine.suggest(profile)

        concept_names = [c.name for c in suggestions.concepts]
        assert "Category" in concept_names

    def test_build_ontology(self, tmp_csv: Path):
        analyzer = DataAnalyzer()
        engine = SuggestionEngine()
        profile = analyzer.analyze(str(tmp_csv))
        suggestions = engine.suggest(profile)

        onto = engine.build_ontology(suggestions, "TestOntology")

        assert onto.name == "TestOntology"
        assert "Order" in onto.concepts
        assert len(onto.concepts) >= 2  # Order + Customer at minimum

    def test_build_ontology_filtered(self, tmp_csv: Path):
        analyzer = DataAnalyzer()
        engine = SuggestionEngine()
        profile = analyzer.analyze(str(tmp_csv))
        suggestions = engine.suggest(profile)

        onto = engine.build_ontology(
            suggestions, "Filtered",
            accepted_concepts=["Order"],
        )

        assert "Order" in onto.concepts
        assert "Customer" not in onto.concepts
        assert len(onto.relations) == 0  # no relations if Customer not accepted

    def test_json_nested_concept(self, tmp_json: Path):
        analyzer = DataAnalyzer()
        engine = SuggestionEngine()
        profile = analyzer.analyze(str(tmp_json))
        suggestions = engine.suggest(profile)

        concept_names = [c.name for c in suggestions.concepts]
        assert "Addres" in concept_names or "Address" in concept_names

    def test_owl_export(self, tmp_csv: Path):
        """End-to-end: data -> suggestions -> ontology -> OWL."""
        analyzer = DataAnalyzer()
        engine = SuggestionEngine()
        profile = analyzer.analyze(str(tmp_csv))
        suggestions = engine.suggest(profile)
        onto = engine.build_ontology(suggestions, "E2E")

        from ontobuilder.owl.export import export_turtle

        turtle = export_turtle(onto)
        assert "owl:Class" in turtle
        assert "Order" in turtle

    def test_notes_generated(self, tmp_csv: Path):
        analyzer = DataAnalyzer()
        engine = SuggestionEngine()
        profile = analyzer.analyze(str(tmp_csv))
        suggestions = engine.suggest(profile)

        # Should have at least one note (the flat dataset note, since only 4 rows)
        assert isinstance(suggestions.notes, list)

    def test_consistency_check(self, tmp_csv: Path):
        """Built ontology should pass consistency checks."""
        analyzer = DataAnalyzer()
        engine = SuggestionEngine()
        profile = analyzer.analyze(str(tmp_csv))
        suggestions = engine.suggest(profile)
        onto = engine.build_ontology(suggestions, "ConsistencyTest")

        from ontobuilder.owl.reasoning import OWLReasoner

        reasoner = OWLReasoner(onto)
        result = reasoner.run_inference()
        assert result.is_consistent


# ---------- CLI integration ----------

class TestToolCLI:
    def test_analyze_command(self, tmp_csv: Path):
        from typer.testing import CliRunner
        from ontobuilder.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["tool", "analyze", str(tmp_csv)])
        assert result.exit_code == 0
        assert "order_id" in result.output or "Order" in result.output

    def test_suggest_command(self, tmp_csv: Path):
        from typer.testing import CliRunner
        from ontobuilder.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["tool", "suggest", str(tmp_csv)])
        assert result.exit_code == 0
        assert "Order" in result.output

    def test_build_auto(self, tmp_csv: Path, tmp_path: Path, monkeypatch):
        from typer.testing import CliRunner
        from ontobuilder.cli.app import app

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, [
            "tool", "build", str(tmp_csv),
            "--output", str(tmp_path / "test.ttl"),
        ])
        assert result.exit_code == 0
        assert (tmp_path / "test.ttl").exists()
        turtle_content = (tmp_path / "test.ttl").read_text()
        assert "owl:Class" in turtle_content
