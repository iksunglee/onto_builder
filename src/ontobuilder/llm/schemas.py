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


# -- Workspace edit commands (for chat-driven ontology modification) --


class AddConceptCmd(BaseModel):
    """Command to add a new class to the ontology."""
    action: str = Field(default="add_concept", description="Must be 'add_concept'")
    name: str = Field(description="Class name")
    description: str = Field(default="", description="Brief description")
    parent: str | None = Field(default=None, description="Parent class name")
    properties: list[PropertySuggestion] = Field(default_factory=list)


class RemoveConceptCmd(BaseModel):
    """Command to remove a class from the ontology."""
    action: str = Field(default="remove_concept", description="Must be 'remove_concept'")
    name: str = Field(description="Class name to remove")


class AddRelationCmd(BaseModel):
    """Command to add a new relation."""
    action: str = Field(default="add_relation", description="Must be 'add_relation'")
    name: str = Field(description="Relation name")
    source: str = Field(description="Source class")
    target: str = Field(description="Target class")
    cardinality: str = Field(default="many-to-many")


class RemoveRelationCmd(BaseModel):
    """Command to remove a relation."""
    action: str = Field(default="remove_relation", description="Must be 'remove_relation'")
    name: str = Field(description="Relation name to remove")


class AddPropertyCmd(BaseModel):
    """Command to add a property to a class."""
    action: str = Field(default="add_property", description="Must be 'add_property'")
    concept: str = Field(description="Class to add property to")
    name: str = Field(description="Property name")
    data_type: str = Field(default="string", description="Data type: string, int, float, bool, date")
    required: bool = Field(default=False)


class RenameConceptCmd(BaseModel):
    """Command to rename a class."""
    action: str = Field(default="rename_concept", description="Must be 'rename_concept'")
    old_name: str = Field(description="Current class name")
    new_name: str = Field(description="New class name")


class AddInstanceCmd(BaseModel):
    """Command to add an individual."""
    action: str = Field(default="add_instance", description="Must be 'add_instance'")
    name: str = Field(description="Instance name")
    concept: str = Field(description="Class this instance belongs to")
    properties: dict[str, object] = Field(default_factory=dict)


class WorkspaceResponse(BaseModel):
    """LLM response during workspace chat - explanation + optional edits."""
    explanation: str = Field(description="Natural language explanation of what you're doing and why")
    edits: list[
        AddConceptCmd | RemoveConceptCmd | AddRelationCmd | RemoveRelationCmd
        | AddPropertyCmd | RenameConceptCmd | AddInstanceCmd
    ] = Field(default_factory=list, description="Ontology edit commands to apply. Empty if just answering a question.")
