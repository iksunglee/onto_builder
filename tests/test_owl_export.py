"""Tests for OWL/RDF export."""

import pytest
from rdflib import Graph
from rdflib.namespace import OWL, RDF, RDFS

from ontobuilder.core.ontology import Ontology

from ontobuilder.owl.export import to_rdflib_graph, export_owl_xml, export_turtle, save_owl


class TestOWLExport:
    def test_produces_valid_rdf_xml(self, pet_store_ontology):
        xml = export_owl_xml(pet_store_ontology)
        g = Graph()
        g.parse(data=xml, format="xml")
        assert len(g) > 0

    def test_produces_valid_turtle(self, pet_store_ontology):
        ttl = export_turtle(pet_store_ontology)
        g = Graph()
        g.parse(data=ttl, format="turtle")
        assert len(g) > 0

    def test_contains_ontology_declaration(self, pet_store_ontology):
        g = to_rdflib_graph(pet_store_ontology)
        ontologies = list(g.subjects(RDF.type, OWL.Ontology))
        assert len(ontologies) == 1

    def test_contains_owl_classes(self, pet_store_ontology):
        g = to_rdflib_graph(pet_store_ontology)
        classes = list(g.subjects(RDF.type, OWL.Class))
        assert len(classes) == len(pet_store_ontology.concepts)

    def test_subclass_relationship(self, pet_store_ontology):
        g = to_rdflib_graph(pet_store_ontology)
        # Dog should be subClassOf Animal
        subclass_pairs = list(g.subject_objects(RDFS.subClassOf))
        # Filter to only URI-to-URI pairs (not restrictions)
        from rdflib import URIRef

        uri_pairs = [(s, o) for s, o in subclass_pairs if isinstance(o, URIRef)]
        assert len(uri_pairs) > 0

    def test_contains_datatype_properties(self, pet_store_ontology):
        g = to_rdflib_graph(pet_store_ontology)
        dt_props = list(g.subjects(RDF.type, OWL.DatatypeProperty))
        assert len(dt_props) > 0

    def test_contains_object_properties(self, pet_store_ontology):
        g = to_rdflib_graph(pet_store_ontology)
        obj_props = list(g.subjects(RDF.type, OWL.ObjectProperty))
        assert len(obj_props) == len(pet_store_ontology.relations)

    def test_contains_named_individuals(self, pet_store_ontology):
        g = to_rdflib_graph(pet_store_ontology)
        individuals = list(g.subjects(RDF.type, OWL.NamedIndividual))
        assert len(individuals) == len(pet_store_ontology.instances)

    def test_custom_namespace(self, pet_store_ontology):
        ns = "https://myontology.org/pets/"
        g = to_rdflib_graph(pet_store_ontology, namespace=ns)
        ontologies = list(g.subjects(RDF.type, OWL.Ontology))
        assert str(ontologies[0]).startswith("https://myontology.org")

    def test_save_to_file(self, pet_store_ontology, tmp_path):
        out = tmp_path / "test.owl"
        result = save_owl(pet_store_ontology, out, fmt="xml")
        assert result.exists()
        g = Graph()
        g.parse(str(out), format="xml")
        assert len(g) > 0

    def test_empty_ontology(self, empty_ontology):
        xml = export_owl_xml(empty_ontology)
        g = Graph()
        g.parse(data=xml, format="xml")
        ontologies = list(g.subjects(RDF.type, OWL.Ontology))
        assert len(ontologies) == 1

    def test_required_property_restriction(self, pet_store_ontology):
        g = to_rdflib_graph(pet_store_ontology)
        restrictions = list(g.subjects(RDF.type, OWL.Restriction))
        assert len(restrictions) > 0

    def test_many_to_one_relation_cardinality_restriction(self):
        onto = Ontology("CardinalityCheck")
        onto.add_concept("Booking")
        onto.add_concept("Room")
        onto.add_relation(
            "assigned_room", source="Booking", target="Room", cardinality="many-to-one"
        )

        g = to_rdflib_graph(onto)
        rel_uri = None
        for subject, _, label in g.triples((None, RDFS.label, None)):
            if str(label) == "assigned_room":
                rel_uri = subject
                break
        assert rel_uri is not None

        restrictions = set(g.subjects(OWL.onProperty, rel_uri))
        assert restrictions
        max_cards = list(g.objects(next(iter(restrictions)), OWL.maxCardinality))
        if not max_cards:
            max_cards = [obj for r in restrictions for obj in g.objects(r, OWL.maxCardinality)]
        assert max_cards
