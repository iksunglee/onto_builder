"""OntoBuilder — A beginner-friendly ontology builder."""

__version__ = "0.1.0"

from ontobuilder.core.model import Concept, Property, Relation, Instance
from ontobuilder.core.ontology import Ontology

__all__ = ["Concept", "Property", "Relation", "Instance", "Ontology"]
