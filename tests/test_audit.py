# tests/test_audit.py
"""Tests for ontology quality auditor."""

from ontobuilder import Ontology
from ontobuilder.tool.audit import OntologyAuditor, AuditResult


class TestAuditResult:
    def test_score_perfect_ontology(self, hospital_ontology):
        auditor = OntologyAuditor()
        result = auditor.audit(hospital_ontology)
        assert isinstance(result, AuditResult)
        assert 0 <= result.score <= 100
        assert isinstance(result.items, list)

    def test_score_empty_ontology(self, empty_ontology):
        auditor = OntologyAuditor()
        result = auditor.audit(empty_ontology)
        assert result.score < 50
        assert any(item.severity == "CRITICAL" for item in result.items)

    def test_result_has_summary(self, hospital_ontology):
        auditor = OntologyAuditor()
        result = auditor.audit(hospital_ontology)
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0

    def test_result_to_dict(self, hospital_ontology):
        auditor = OntologyAuditor()
        result = auditor.audit(hospital_ontology)
        d = result.to_dict()
        assert "score" in d
        assert "items" in d
        assert isinstance(d["items"], list)


class TestAuditChecks:
    def test_missing_descriptions(self):
        onto = Ontology("Test")
        onto.add_concept("Foo")
        onto.add_concept("Bar", description="Has one")
        auditor = OntologyAuditor()
        result = auditor.audit(onto)
        desc_items = [i for i in result.items if i.check == "missing_descriptions"]
        assert len(desc_items) > 0
        assert any("Foo" in i.detail for i in desc_items)

    def test_orphan_concepts(self):
        onto = Ontology("Test")
        onto.add_concept("A", description="A thing")
        onto.add_concept("B", description="B thing")
        auditor = OntologyAuditor()
        result = auditor.audit(onto)
        orphan_items = [i for i in result.items if i.check == "orphan_concepts"]
        assert len(orphan_items) > 0

    def test_sparse_properties(self):
        onto = Ontology("Test")
        onto.add_concept("Sparse", description="Has no properties")
        auditor = OntologyAuditor()
        result = auditor.audit(onto)
        sparse_items = [i for i in result.items if i.check == "sparse_properties"]
        assert len(sparse_items) > 0

    def test_hierarchy_too_flat(self):
        onto = Ontology("Test")
        for i in range(6):
            onto.add_concept(f"C{i}", description=f"Concept {i}")
        auditor = OntologyAuditor()
        result = auditor.audit(onto)
        hierarchy_items = [i for i in result.items if i.check == "hierarchy_issues"]
        assert len(hierarchy_items) > 0

    def test_naming_inconsistencies(self):
        onto = Ontology("Test")
        onto.add_concept("MyClass", description="PascalCase")
        onto.add_concept("my_other_class", description="snake_case")
        auditor = OntologyAuditor()
        result = auditor.audit(onto)
        naming_items = [i for i in result.items if i.check == "naming_inconsistencies"]
        assert len(naming_items) > 0

    def test_instance_coverage(self):
        onto = Ontology("Test")
        onto.add_concept("HasInstances", description="Has some")
        onto.add_concept("NoInstances", description="Has none")
        onto.add_instance("i1", concept="HasInstances", properties={"a": 1})
        auditor = OntologyAuditor()
        result = auditor.audit(onto)
        coverage_items = [i for i in result.items if i.check == "instance_coverage"]
        assert len(coverage_items) > 0
        assert any("NoInstances" in i.detail for i in coverage_items)

    def test_no_concepts_is_critical(self):
        onto = Ontology("Empty")
        auditor = OntologyAuditor()
        result = auditor.audit(onto)
        assert any(
            i.severity == "CRITICAL" and i.check == "no_concepts"
            for i in result.items
        )

    def test_well_formed_ontology_scores_high(self, hospital_ontology):
        auditor = OntologyAuditor()
        result = auditor.audit(hospital_ontology)
        assert result.score >= 70

    def test_severity_levels(self, empty_ontology):
        auditor = OntologyAuditor()
        result = auditor.audit(empty_ontology)
        for item in result.items:
            assert item.severity in ("CRITICAL", "WARNING", "SUGGESTION")
