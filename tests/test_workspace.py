"""Tests for OntologyWorkspace (non-LLM parts). """

import pytest

from ontobuilder.core.ontology import Ontology
from ontobuilder.chat.workspace import OntologyWorkspace, _serialize_ontology_state


class TestWorkspaceFromExisting:
    def test_create_from_ontology(self, pet_store_ontology):
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        assert ws.onto.name == pet_store_ontology.name
        assert len(ws.onto.concepts) == len(pet_store_ontology.concepts)

    def test_get_state(self, pet_store_ontology):
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        state = ws.get_state()
        assert "OWL Classes" in state
        assert pet_store_ontology.name in state

    def test_export_owl_turtle(self, pet_store_ontology):
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        ttl = ws.export_owl("turtle")
        assert "owl:Class" in ttl
        assert "owl:Ontology" in ttl

    def test_export_owl_xml(self, pet_store_ontology):
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        xml = ws.export_owl("xml")
        assert "owl:Ontology" in xml or "Ontology" in xml

    def test_save_owl(self, pet_store_ontology, tmp_path):
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        out = tmp_path / "test.ttl"
        result = ws.save_owl(out, fmt="turtle")
        assert result.exists()
        content = result.read_text()
        assert "owl:Class" in content

    def test_run_inference(self, pet_store_ontology):
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        summary = ws.run_inference()
        assert "Inference results" in summary

    def test_edit_log_starts_empty(self, pet_store_ontology):
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        assert ws.get_edit_log() == []


class TestWorkspaceEdits:
    """Test the _apply_edit method directly (no LLM needed)."""

    def test_apply_add_concept(self, pet_store_ontology):
        from ontobuilder.llm.schemas import AddConceptCmd
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        cmd = AddConceptCmd(name="Bird", description="A flying animal", parent="Animal")
        desc = ws._apply_edit(cmd)
        assert "Bird" in ws.onto.concepts
        assert ws.onto.concepts["Bird"].parent == "Animal"
        assert "Added class" in desc

    def test_apply_remove_concept(self, pet_store_ontology):
        from ontobuilder.llm.schemas import RemoveConceptCmd
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        initial = len(ws.onto.concepts)
        cmd = RemoveConceptCmd(name="Poodle")
        ws._apply_edit(cmd)
        assert "Poodle" not in ws.onto.concepts
        assert len(ws.onto.concepts) == initial - 1

    def test_apply_add_relation(self, pet_store_ontology):
        from ontobuilder.llm.schemas import AddRelationCmd
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        cmd = AddRelationCmd(name="fears", source="Dog", target="Animal", cardinality="many-to-many")
        ws._apply_edit(cmd)
        assert "fears" in ws.onto.relations

    def test_apply_remove_relation(self, pet_store_ontology):
        from ontobuilder.llm.schemas import AddRelationCmd, RemoveRelationCmd
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        # Add one first
        ws._apply_edit(AddRelationCmd(name="test_rel", source="Dog", target="Animal"))
        assert "test_rel" in ws.onto.relations
        ws._apply_edit(RemoveRelationCmd(name="test_rel"))
        assert "test_rel" not in ws.onto.relations

    def test_apply_add_property(self, pet_store_ontology):
        from ontobuilder.llm.schemas import AddPropertyCmd
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        cmd = AddPropertyCmd(concept="Dog", name="color", data_type="string", required=False)
        ws._apply_edit(cmd)
        dog = ws.onto.concepts["Dog"]
        assert any(p.name == "color" for p in dog.properties)

    def test_apply_rename_concept(self, pet_store_ontology):
        from ontobuilder.llm.schemas import RenameConceptCmd
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        cmd = RenameConceptCmd(old_name="Dog", new_name="Canine")
        ws._apply_edit(cmd)
        assert "Canine" in ws.onto.concepts
        assert "Dog" not in ws.onto.concepts
        # Children should be updated
        assert ws.onto.concepts["Poodle"].parent == "Canine"

    def test_apply_add_instance(self, pet_store_ontology):
        from ontobuilder.llm.schemas import AddInstanceCmd
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        cmd = AddInstanceCmd(name="Sparky", concept="Dog", properties={"breed": "labrador"})
        ws._apply_edit(cmd)
        assert "Sparky" in ws.onto.instances
        assert ws.onto.instances["Sparky"].concept == "Dog"

    def test_edit_log_tracks_changes(self, pet_store_ontology):
        from ontobuilder.llm.schemas import AddConceptCmd, AddRelationCmd
        ws = OntologyWorkspace.from_existing(pet_store_ontology)
        ws._apply_edit(AddConceptCmd(name="Fish", description="Aquatic"))
        ws._apply_edit(AddRelationCmd(name="hunts", source="Animal", target="Fish"))
        log = ws.get_edit_log()
        assert len(log) == 2
        assert log[0]["action"] == "add_concept"
        assert log[1]["action"] == "add_relation"
        assert log[1]["name"] == "hunts"


class TestSerializeState:
    def test_serialize(self, pet_store_ontology):
        state = _serialize_ontology_state(pet_store_ontology)
        assert "OWL Classes" in state
        assert "OWL ObjectProperties" in state
        assert "OWL NamedIndividuals" in state

    def test_empty_ontology(self, empty_ontology):
        state = _serialize_ontology_state(empty_ontology)
        assert "Classes: 0" in state
