# tests/test_compare.py
"""Tests for ontology compare / diff."""

import pytest
from ontobuilder import Ontology
from ontobuilder.tool.compare import OntologyDiff, diff_ontologies, merge_ontologies


class TestDiffStructure:
    def test_identical_ontologies(self, hospital_ontology):
        result = diff_ontologies(hospital_ontology, hospital_ontology)
        assert isinstance(result, OntologyDiff)
        assert len(result.only_in_a.concepts) == 0
        assert len(result.only_in_b.concepts) == 0

    def test_diff_has_summary(self, pet_store_ontology, hospital_ontology):
        result = diff_ontologies(pet_store_ontology, hospital_ontology)
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0

    def test_diff_to_dict(self, pet_store_ontology, hospital_ontology):
        result = diff_ontologies(pet_store_ontology, hospital_ontology)
        d = result.to_dict()
        assert "only_in_a" in d
        assert "only_in_b" in d
        assert "modified" in d


class TestDiffConcepts:
    def test_concepts_only_in_a(self):
        a = Ontology("A")
        a.add_concept("Foo", description="In A")
        a.add_concept("Shared", description="In both")

        b = Ontology("B")
        b.add_concept("Shared", description="In both")

        result = diff_ontologies(a, b)
        assert "Foo" in result.only_in_a.concepts
        assert "Shared" not in result.only_in_a.concepts

    def test_concepts_only_in_b(self):
        a = Ontology("A")
        a.add_concept("Shared", description="In both")

        b = Ontology("B")
        b.add_concept("Shared", description="In both")
        b.add_concept("Bar", description="In B")

        result = diff_ontologies(a, b)
        assert "Bar" in result.only_in_b.concepts
        assert "Shared" not in result.only_in_b.concepts

    def test_modified_concepts(self):
        a = Ontology("A")
        a.add_concept("Thing", description="Version A")

        b = Ontology("B")
        b.add_concept("Thing", description="Version B")

        result = diff_ontologies(a, b)
        assert any(m["name"] == "Thing" for m in result.modified)


class TestDiffRelations:
    def test_relations_only_in_a(self):
        a = Ontology("A")
        a.add_concept("X", description="X")
        a.add_concept("Y", description="Y")
        a.add_relation("links", source="X", target="Y")

        b = Ontology("B")
        b.add_concept("X", description="X")
        b.add_concept("Y", description="Y")

        result = diff_ontologies(a, b)
        assert "links" in result.only_in_a.relations

    def test_relations_only_in_b(self):
        a = Ontology("A")
        a.add_concept("X", description="X")
        a.add_concept("Y", description="Y")

        b = Ontology("B")
        b.add_concept("X", description="X")
        b.add_concept("Y", description="Y")
        b.add_relation("connects", source="X", target="Y")

        result = diff_ontologies(a, b)
        assert "connects" in result.only_in_b.relations


class TestDiffInstances:
    def test_instances_only_in_a(self):
        a = Ontology("A")
        a.add_concept("C", description="C")
        a.add_instance("i1", concept="C", properties={"x": 1})

        b = Ontology("B")
        b.add_concept("C", description="C")

        result = diff_ontologies(a, b)
        assert "i1" in result.only_in_a.instances


class TestMerge:
    def test_merge_adds_b_only_concepts(self):
        a = Ontology("A")
        a.add_concept("Shared", description="In both")

        b = Ontology("B")
        b.add_concept("Shared", description="In both")
        b.add_concept("NewFromB", description="Only in B")

        merged = merge_ontologies(a, b)
        assert "Shared" in merged.concepts
        assert "NewFromB" in merged.concepts

    def test_merge_adds_b_only_relations(self):
        a = Ontology("A")
        a.add_concept("X", description="X")
        a.add_concept("Y", description="Y")

        b = Ontology("B")
        b.add_concept("X", description="X")
        b.add_concept("Y", description="Y")
        b.add_relation("links", source="X", target="Y")

        merged = merge_ontologies(a, b)
        assert "links" in merged.relations

    def test_merge_preserves_a_data(self):
        a = Ontology("A", description="A desc")
        a.add_concept("OnlyA", description="A only")

        b = Ontology("B")

        merged = merge_ontologies(a, b)
        assert merged.name == "A"
        assert "OnlyA" in merged.concepts

    def test_merge_adds_b_only_instances(self):
        a = Ontology("A")
        a.add_concept("C", description="C")

        b = Ontology("B")
        b.add_concept("C", description="C")
        b.add_instance("i1", concept="C", properties={"v": 1})

        merged = merge_ontologies(a, b)
        assert "i1" in merged.instances
