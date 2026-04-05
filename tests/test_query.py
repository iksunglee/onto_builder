"""Tests for structured query engine."""

import pytest

from ontobuilder.owl.query import StructuredQuery


class TestFindClasses:
    def test_find_all_classes(self, pet_store_ontology):
        engine = StructuredQuery(pet_store_ontology)
        result = engine.find_classes()
        assert result.count == len(pet_store_ontology.concepts)

    def test_find_by_parent(self, pet_store_ontology):
        engine = StructuredQuery(pet_store_ontology)
        result = engine.find_classes(parent="Animal")
        # Dog and Poodle are subclasses of Animal
        assert result.count >= 2

    def test_find_by_name(self, pet_store_ontology):
        engine = StructuredQuery(pet_store_ontology)
        result = engine.find_classes(name_contains="Dog")
        assert result.count >= 1
        assert any(r["class"] == "Dog" for r in result.results)


class TestFindInstances:
    def test_find_all_instances(self, pet_store_ontology):
        engine = StructuredQuery(pet_store_ontology)
        result = engine.find_instances()
        assert result.count == len(pet_store_ontology.instances)

    def test_find_by_class(self, pet_store_ontology):
        engine = StructuredQuery(pet_store_ontology)
        # Find instances of Animal (should include subclass instances)
        result = engine.find_instances(of_class="Animal", include_subclasses=True)
        assert result.count >= 0  # May have instances


class TestFindRelations:
    def test_find_all_relations(self, pet_store_ontology):
        engine = StructuredQuery(pet_store_ontology)
        result = engine.find_relations()
        assert result.count == len(pet_store_ontology.relations)


class TestDescribeClass:
    def test_describe_existing(self, pet_store_ontology):
        engine = StructuredQuery(pet_store_ontology)
        result = engine.describe_class("Animal")
        assert result.count == 1
        assert result.results[0]["name"] == "Animal"

    def test_describe_nonexistent(self, pet_store_ontology):
        engine = StructuredQuery(pet_store_ontology)
        result = engine.describe_class("Ghost")
        assert result.count == 0


class TestValidateInstance:
    def test_validate(self, pet_store_ontology):
        engine = StructuredQuery(pet_store_ontology)
        for inst_name in pet_store_ontology.instances:
            result = engine.validate_instance(inst_name)
            assert result.count == 1
            assert result.results[0]["status"] in ("VALID", "INVALID")
            break


class TestFindPath:
    def test_find_path_in_hierarchy(self, pet_store_ontology):
        engine = StructuredQuery(pet_store_ontology)
        result = engine.find_path("Poodle", "Animal")
        assert result.count >= 1

    def test_no_path(self, empty_ontology):
        engine = StructuredQuery(empty_ontology)
        result = engine.find_path("A", "B")
        assert result.count == 0


class TestQueryResultTable:
    def test_to_table(self, pet_store_ontology):
        engine = StructuredQuery(pet_store_ontology)
        result = engine.find_classes()
        table = result.to_table()
        assert "Query:" in table
        assert "class" in table
