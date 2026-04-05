"""Tests for chat-based ontology checker (keyword mode, no LLM required)."""

import pytest

from ontobuilder.chat.checker import OntologyChat


class TestKeywordChat:
    def test_count_classes(self, pet_store_ontology):
        chat = OntologyChat(pet_store_ontology)
        answer = chat.ask("How many classes are there?")
        assert str(len(pet_store_ontology.concepts)) in answer

    def test_count_relations(self, pet_store_ontology):
        chat = OntologyChat(pet_store_ontology)
        answer = chat.ask("How many relations?")
        assert str(len(pet_store_ontology.relations)) in answer

    def test_count_instances(self, pet_store_ontology):
        chat = OntologyChat(pet_store_ontology)
        answer = chat.ask("How many instances?")
        assert str(len(pet_store_ontology.instances)) in answer

    def test_consistency_check(self, pet_store_ontology):
        chat = OntologyChat(pet_store_ontology)
        answer = chat.ask("Is the ontology consistent?")
        assert "consistent" in answer.lower() or "issue" in answer.lower()

    def test_show_hierarchy(self, pet_store_ontology):
        chat = OntologyChat(pet_store_ontology)
        answer = chat.ask("Show the hierarchy")
        assert "Ontology:" in answer

    def test_describe_class(self, pet_store_ontology):
        chat = OntologyChat(pet_store_ontology)
        answer = chat.ask("Describe Animal")
        assert "Animal" in answer

    def test_summary(self, pet_store_ontology):
        chat = OntologyChat(pet_store_ontology)
        answer = chat.ask("Give me a summary")
        assert "Inference results" in answer

    def test_subclass_query(self, pet_store_ontology):
        chat = OntologyChat(pet_store_ontology)
        answer = chat.ask("What are the children of Animal?")
        assert "Dog" in answer

    def test_fallback_for_unknown(self, pet_store_ontology):
        chat = OntologyChat(pet_store_ontology)
        answer = chat.ask("xyzzy random gibberish")
        # Should get fallback help text
        assert len(answer) > 0

    def test_reset_history(self, pet_store_ontology):
        chat = OntologyChat(pet_store_ontology)
        chat.ask("summary")
        chat.reset()
        assert len(chat._history) == 0

    def test_infer_user_intent_for_empty_ontology(self, empty_ontology):
        chat = OntologyChat(empty_ontology)
        suggestions = chat.infer_user_intent(limit=3)
        assert len(suggestions) == 3
        assert "first core concept" in suggestions[0].lower()

    def test_infer_user_intent_for_populated_ontology(self, pet_store_ontology):
        chat = OntologyChat(pet_store_ontology)
        suggestions = chat.infer_user_intent(limit=5)
        assert suggestions
        assert any("export to owl/turtle" in suggestion.lower() for suggestion in suggestions)

    def test_keyword_next_step_recommendation(self, pet_store_ontology):
        chat = OntologyChat(pet_store_ontology)
        answer = chat.ask("What should I do next?")
        assert "likely want to do these next steps" in answer.lower()

    def test_check_subclasses_not_misrouted_to_consistency(self, pet_store_ontology):
        chat = OntologyChat(pet_store_ontology)
        answer = chat.ask("check subclasses of Animal")
        assert "subclasses of animal" in answer.lower()

    def test_suggest_subclasses_not_misrouted_to_next_steps(self, pet_store_ontology):
        chat = OntologyChat(pet_store_ontology)
        answer = chat.ask("suggest subclasses of Animal")
        assert "subclasses of animal" in answer.lower()
