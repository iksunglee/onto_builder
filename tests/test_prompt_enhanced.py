"""Tests for enhanced system prompt builder."""

from ontobuilder.serialization.prompt_enhanced import export_enhanced_prompt


class TestEnhancedPromptSections:
    def test_has_domain_overview(self, hospital_ontology):
        prompt = export_enhanced_prompt(hospital_ontology)
        assert "# Domain: Hospital Operations" in prompt
        assert "Surgical scheduling" in prompt

    def test_has_core_concepts(self, hospital_ontology):
        prompt = export_enhanced_prompt(hospital_ontology)
        assert "## Core Concepts" in prompt
        assert "Surgeon" in prompt
        assert "OperatingRoom" in prompt

    def test_has_relationships(self, hospital_ontology):
        prompt = export_enhanced_prompt(hospital_ontology)
        assert "## Relationships & Rules" in prompt
        assert "performs" in prompt
        assert "one-to-many" in prompt

    def test_has_constraints(self, hospital_ontology):
        prompt = export_enhanced_prompt(hospital_ontology)
        assert "## Constraints" in prompt
        assert "no-double-booking" in prompt
        assert "Room is already booked" in prompt

    def test_has_valid_values(self, hospital_ontology):
        prompt = export_enhanced_prompt(hospital_ontology)
        assert "## Valid Values" in prompt

    def test_has_scenarios(self, hospital_ontology):
        prompt = export_enhanced_prompt(hospital_ontology)
        assert "reserve-operating-room" in prompt

    def test_empty_ontology(self, empty_ontology):
        prompt = export_enhanced_prompt(empty_ontology)
        assert "# Domain: Empty" in prompt


class TestEnhancedPromptSectionsFilter:
    def test_sections_filter(self, hospital_ontology):
        prompt = export_enhanced_prompt(hospital_ontology, sections=["concepts"])
        assert "## Core Concepts" in prompt
        assert "## Relationships" not in prompt
        assert "## Constraints" not in prompt

    def test_sections_multiple(self, hospital_ontology):
        prompt = export_enhanced_prompt(hospital_ontology, sections=["concepts", "rules"])
        assert "## Core Concepts" in prompt
        assert "## Relationships & Rules" in prompt
        assert "## Constraints" not in prompt


class TestQueryLogic:
    def test_with_queries_flag(self, hospital_ontology):
        prompt = export_enhanced_prompt(hospital_ontology, with_queries=True)
        assert "## Query Logic" in prompt
        assert "Identify Intent" in prompt
        assert "Resolve Entities" in prompt
        assert "Validate Constraints" in prompt

    def test_without_queries_flag(self, hospital_ontology):
        prompt = export_enhanced_prompt(hospital_ontology, with_queries=False)
        assert "## Query Logic" not in prompt


class TestAudience:
    def test_developer_audience(self, hospital_ontology):
        prompt = export_enhanced_prompt(hospital_ontology, audience="developer")
        assert "JSON Schema" in prompt or "schema" in prompt.lower()

    def test_enduser_audience(self, hospital_ontology):
        prompt = export_enhanced_prompt(hospital_ontology, audience="enduser")
        assert "JSON Schema" not in prompt
