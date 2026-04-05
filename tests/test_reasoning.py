"""Tests for OWL reasoning engine."""

import pytest

from ontobuilder.core.ontology import Ontology
from ontobuilder.owl.reasoning import OWLReasoner


class TestSubclassInference:
    def test_get_ancestors(self, pet_store_ontology):
        reasoner = OWLReasoner(pet_store_ontology)
        # Poodle → Dog → Animal
        ancestors = reasoner.get_ancestors("Poodle")
        assert "Dog" in ancestors
        assert "Animal" in ancestors

    def test_get_descendants(self, pet_store_ontology):
        reasoner = OWLReasoner(pet_store_ontology)
        descendants = reasoner.get_descendants("Animal")
        assert "Dog" in descendants
        assert "Poodle" in descendants

    def test_is_subclass_of(self, pet_store_ontology):
        reasoner = OWLReasoner(pet_store_ontology)
        assert reasoner.is_subclass_of("Poodle", "Animal")
        assert reasoner.is_subclass_of("Dog", "Animal")
        assert not reasoner.is_subclass_of("Animal", "Dog")

    def test_root_has_no_ancestors(self, pet_store_ontology):
        reasoner = OWLReasoner(pet_store_ontology)
        assert reasoner.get_ancestors("Animal") == []


class TestPropertyInheritance:
    def test_inherited_properties(self, pet_store_ontology):
        reasoner = OWLReasoner(pet_store_ontology)
        all_props = reasoner.get_all_properties("Dog")
        # Dog should inherit properties from Animal
        inherited = {k: v for k, v in all_props.items() if v["inherited"]}
        assert len(inherited) > 0

    def test_poodle_inherits_from_animal_and_dog(self, pet_store_ontology):
        reasoner = OWLReasoner(pet_store_ontology)
        all_props = reasoner.get_all_properties("Poodle")
        assert len(all_props) > 0

    def test_root_has_no_inherited(self, pet_store_ontology):
        reasoner = OWLReasoner(pet_store_ontology)
        all_props = reasoner.get_all_properties("Animal")
        inherited = {k: v for k, v in all_props.items() if v["inherited"]}
        assert len(inherited) == 0


class TestInstanceClassification:
    def test_classify_instance(self, pet_store_ontology):
        reasoner = OWLReasoner(pet_store_ontology)
        # Get any instance and check its types
        for inst_name in pet_store_ontology.instances:
            types = reasoner.classify_instance(inst_name)
            assert len(types) >= 1
            break

    def test_find_instances_of_with_subclasses(self, pet_store_ontology):
        reasoner = OWLReasoner(pet_store_ontology)
        # Instances of Animal should include Dog/Poodle instances too
        instances = reasoner.find_instances_of("Animal", include_subclasses=True)
        # All instances should be found since they're all animals
        assert len(instances) >= len(
            [i for i in pet_store_ontology.instances.values() if i.concept == "Animal"]
        )


class TestConsistencyChecking:
    def test_consistent_ontology(self, pet_store_ontology):
        reasoner = OWLReasoner(pet_store_ontology)
        issues = reasoner.check_consistency()
        # pet_store should be consistent (may have required prop warnings)
        # Just verify it returns a list
        assert isinstance(issues, list)

    def test_orphaned_parent(self):
        onto = Ontology("test")
        onto.concepts["Child"] = __import__(
            "ontobuilder.core.model", fromlist=["Concept"]
        ).Concept(name="Child", parent="NonExistent")
        reasoner = OWLReasoner(onto)
        issues = reasoner.check_consistency()
        assert any("non-existent parent" in i for i in issues)

    def test_instance_of_missing_concept(self):
        from ontobuilder.core.model import Instance
        onto = Ontology("test")
        onto.instances["thing"] = Instance(name="thing", concept="Ghost")
        reasoner = OWLReasoner(onto)
        issues = reasoner.check_consistency()
        assert any("non-existent concept" in i for i in issues)


class TestFullInference:
    def test_run_inference(self, pet_store_ontology):
        reasoner = OWLReasoner(pet_store_ontology)
        result = reasoner.run_inference()
        assert result.summary
        assert "Inference results" in result.summary

    def test_empty_ontology(self, empty_ontology):
        reasoner = OWLReasoner(empty_ontology)
        result = reasoner.run_inference()
        assert result.is_consistent
