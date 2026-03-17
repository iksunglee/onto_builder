"""Base class for domain builders."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ontobuilder.core.ontology import Ontology


class DomainBuilder(ABC):
    """Abstract base class for domain-specific ontology templates."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Domain name (e.g., 'ecommerce', 'healthcare')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief description of this domain."""
        ...

    @abstractmethod
    def build_template(self) -> Ontology:
        """Create a pre-populated ontology template for this domain."""
        ...

    def get_interview_hints(self) -> dict:
        """Return hints to guide the LLM interview for this domain."""
        return {"domain": self.name, "description": self.description}

    def get_glossary(self) -> dict[str, str]:
        """Return domain-specific glossary terms."""
        return {}
