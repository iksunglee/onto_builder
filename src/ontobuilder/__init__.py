"""OntoBuilder — A beginner-friendly ontology builder."""

__version__ = "0.1.4"

from ontobuilder.core.model import Concept, Property, Relation, Instance
from ontobuilder.core.ontology import Ontology

__all__ = [
    "Concept", "Property", "Relation", "Instance", "Ontology",
    "OWLReasoner", "StructuredQuery", "OntologyChat",
]


def __getattr__(name: str):
    """Lazy imports for new modules."""
    if name == "OWLReasoner":
        from ontobuilder.owl.reasoning import OWLReasoner
        return OWLReasoner
    if name == "StructuredQuery":
        from ontobuilder.owl.query import StructuredQuery
        return StructuredQuery
    if name == "OntologyChat":
        from ontobuilder.chat.checker import OntologyChat
        return OntologyChat
    raise AttributeError(f"module 'ontobuilder' has no attribute {name!r}")
