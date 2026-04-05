"""Tests for LLM inference helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path


def test_build_analysis_context_detects_fk_and_relations(tmp_path: Path):
    from ontobuilder.llm.inference import _build_analysis_context

    path = tmp_path / "orders.csv"
    rows = [
        {
            "order_id": str(i),
            "customer_id": str(100 + (i % 5)),
            "category": ["Books", "Games", "Home"][i % 3],
            "product_name": f"Product {i}",
            "tags": "featured,seasonal" if i % 2 == 0 else "clearance,discount",
        }
        for i in range(60)
    ]

    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    ctx = _build_analysis_context(path)

    assert "Total rows: 60" in ctx
    assert "customer_id" in ctx
    assert "foreign key" in ctx
    assert "Customer" in ctx


def test_build_analysis_context_empty_for_text(tmp_path: Path):
    from ontobuilder.llm.inference import _build_analysis_context

    path = tmp_path / "notes.txt"
    path.write_text("just some text\nanother line\n", encoding="utf-8")

    ctx = _build_analysis_context(path)
    assert ctx == ""


def test_infer_prompt_includes_sample_data():
    from ontobuilder.llm.prompts import infer_prompt

    messages = infer_prompt("col_a | col_b\n--- | ---\n1 | hello")

    content = messages[1]["content"]
    assert "col_a | col_b" in content
    assert "1 | hello" in content


def test_infer_prompt_includes_analysis_context():
    from ontobuilder.llm.prompts import infer_prompt

    messages = infer_prompt(
        "col_a | col_b\n--- | ---\n1 | hello",
        analysis_context="Total rows: 120\ncustomer_id: likely foreign key",
    )

    content = messages[1]["content"]
    assert "Total rows: 120" in content
    assert "col_a | col_b" in content
