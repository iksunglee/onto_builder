"""Pydantic schemas for structured LLM output."""

from __future__ import annotations

try:
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError("LLM features require: pip install ontobuilder[llm]")


class PropertySuggestion(BaseModel):
    name: str = Field(description="Property name")
    data_type: str = Field(default="string", description="Data type: string, int, float, bool, date")
    required: bool = Field(default=False)


class ConceptSuggestion(BaseModel):
    name: str = Field(description="Concept name")
    description: str = Field(default="", description="Brief description")
    parent: str | None = Field(default=None, description="Parent concept name if any")
    properties: list[PropertySuggestion] = Field(default_factory=list)


class RelationSuggestion(BaseModel):
    name: str = Field(description="Relation name")
    source: str = Field(description="Source concept")
    target: str = Field(description="Target concept")
    cardinality: str = Field(default="many-to-many")


class OntologySuggestion(BaseModel):
    """Complete ontology structure suggested by the LLM."""
    name: str = Field(description="Ontology name")
    description: str = Field(default="")
    concepts: list[ConceptSuggestion] = Field(default_factory=list)
    relations: list[RelationSuggestion] = Field(default_factory=list)


class InterviewQuestion(BaseModel):
    """A question the LLM wants to ask during the interview."""
    question: str = Field(description="The question to ask the user")
    purpose: str = Field(description="Why this question helps build the ontology")


class InterviewQuestions(BaseModel):
    """A set of scoping questions."""
    questions: list[InterviewQuestion] = Field(
        description="Questions to ask the user about their domain"
    )
