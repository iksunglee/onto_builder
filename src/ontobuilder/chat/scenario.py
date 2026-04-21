"""Scenario-based ontology builder — Ontology Reasoning Engine.

Interprets real-world scenario descriptions and generates structured
ontologies through a 6-step reasoning process:
1. Identify scenario type
2. Extract ontology components
3. Map to ontology graph
4. Reason over graph
5. Generate 3-layer output
6. Convert to optimization logic (if applicable)
"""

from __future__ import annotations

from typing import Any

from ontobuilder.core.ontology import Ontology
from ontobuilder.core.validation import VALID_DATA_TYPES, ValidationError
from ontobuilder.owl.reasoning import OWLReasoner


def _build_ontology_from_analysis(
    analysis: Any,
    name: str = "ScenarioOntology",
) -> Ontology:
    """Convert a ScenarioAnalysis into an Ontology object."""
    onto = Ontology(name, description=analysis.explanation[:200])

    # Add hierarchy concepts first (they have parent refs)
    added: set[str] = set()
    for concept in analysis.hierarchy:
        parent = concept.parent if concept.parent and concept.parent in added else None
        onto.add_concept(concept.name, description=concept.description, parent=parent)
        added.add(concept.name)
        for prop in concept.properties:
            dt = prop.data_type if prop.data_type in VALID_DATA_TYPES else "string"
            onto.add_property(concept.name, prop.name, data_type=dt, required=prop.required)

    # Add remaining entities not covered by hierarchy
    for entity in analysis.entities:
        if entity.name not in onto.concepts:
            onto.add_concept(entity.name, description=entity.description)
            added.add(entity.name)
            for attr in entity.attributes:
                dt = attr.data_type if attr.data_type in VALID_DATA_TYPES else "string"
                onto.add_property(entity.name, attr.name, data_type=dt, required=attr.required)

    # Add relationships (only if both endpoints exist)
    for edge in analysis.relationships:
        if edge.source in onto.concepts and edge.target in onto.concepts:
            onto.add_relation(
                edge.relationship,
                source=edge.source,
                target=edge.target,
                cardinality=edge.cardinality,
            )

    return onto


class ScenarioBuilder:
    """Build and refine ontologies from scenario descriptions."""

    def __init__(self) -> None:
        self.onto: Ontology | None = None
        self.scenario_type: str = ""
        self.constraints: list[str] = []
        self.goals: list[str] = []
        self.recommendations: list[str] = []
        self.optimization_notes: str = ""
        self._history: list[dict[str, str]] = []

    def analyze(self, scenario: str, name: str = "ScenarioOntology") -> dict[str, Any]:
        """Analyze a scenario and build an ontology from it.

        Returns a dict with:
        - scenario_type: str
        - explanation: str
        - ontology: Ontology object
        - constraints: list[str]
        - goals: list[str]
        - recommendations: list[str]
        - optimization_notes: str
        """
        from ontobuilder.llm.client import chat
        from ontobuilder.llm.prompts import SCENARIO_SYSTEM, SCENARIO_ANALYZE
        from ontobuilder.llm.schemas import ScenarioAnalysis

        existing_context = ""
        if self.onto and self.onto.concepts:
            from ontobuilder.chat.workspace import _serialize_ontology_state

            existing_context = (
                "Existing ontology to extend:\n"
                + _serialize_ontology_state(self.onto)
            )

        messages = [
            {"role": "system", "content": SCENARIO_SYSTEM},
            {
                "role": "user",
                "content": SCENARIO_ANALYZE.format(
                    scenario=scenario, existing_context=existing_context
                ),
            },
        ]

        analysis: ScenarioAnalysis = chat(messages, response_model=ScenarioAnalysis)

        self.onto = _build_ontology_from_analysis(analysis, name=name)
        self.scenario_type = analysis.scenario_type
        self.constraints = list(analysis.constraints)
        self.goals = list(analysis.goals)
        self.recommendations = list(analysis.recommendations)
        self.optimization_notes = analysis.optimization_notes

        return {
            "scenario_type": self.scenario_type,
            "explanation": analysis.explanation,
            "ontology": self.onto,
            "constraints": self.constraints,
            "goals": self.goals,
            "recommendations": self.recommendations,
            "optimization_notes": self.optimization_notes,
        }

    def refine(self, message: str) -> dict[str, Any]:
        """Refine the scenario ontology via chat.

        Returns:
            Dict with keys:
            - explanation: str
            - edits_applied: list[str]
            - errors: list[str]
            - updated_constraints: list[str]
            - updated_goals: list[str]
        """
        if self.onto is None:
            raise ValueError("No ontology built yet. Call analyze() first.")

        from ontobuilder.llm.client import chat
        from ontobuilder.llm.prompts import SCENARIO_SYSTEM, SCENARIO_REFINE
        from ontobuilder.llm.schemas import ScenarioRefineResponse
        from ontobuilder.chat.workspace import _serialize_ontology_state

        state = _serialize_ontology_state(self.onto)
        messages = [
            {"role": "system", "content": SCENARIO_SYSTEM},
        ]
        messages.extend(self._history)
        messages.append(
            {
                "role": "user",
                "content": SCENARIO_REFINE.format(
                    ontology_state=state,
                    scenario_type=self.scenario_type,
                    user_message=message,
                ),
            },
        )

        response: ScenarioRefineResponse = chat(
            messages, response_model=ScenarioRefineResponse
        )

        # Apply edits
        edits_applied: list[str] = []
        errors: list[str] = []
        for edit in response.edits:
            try:
                desc = self._apply_edit(edit)
                edits_applied.append(desc)
            except (ValidationError, Exception) as e:
                errors.append(f"{edit.action}: {e}")

        # Update metadata
        if response.updated_constraints:
            self.constraints = list(response.updated_constraints)
        if response.updated_goals:
            self.goals = list(response.updated_goals)

        # Update history
        self._history.append({"role": "user", "content": message})
        edit_summary = ""
        if edits_applied:
            edit_summary = "\n[Applied: " + ", ".join(edits_applied) + "]"
        self._history.append(
            {"role": "assistant", "content": response.explanation + edit_summary}
        )

        if len(self._history) > 40:
            self._history = self._history[-20:]

        return {
            "explanation": response.explanation,
            "edits_applied": edits_applied,
            "errors": errors,
            "updated_constraints": self.constraints,
            "updated_goals": self.goals,
        }

    def _apply_edit(self, edit: Any) -> str:
        """Apply a single edit command. Returns description."""
        assert self.onto is not None
        action = edit.action

        if action == "add_concept":
            parent = (
                edit.parent
                if hasattr(edit, "parent") and edit.parent and edit.parent in self.onto.concepts
                else None
            )
            self.onto.add_concept(edit.name, description=getattr(edit, "description", ""), parent=parent)
            for p in getattr(edit, "properties", []):
                dt = p.data_type if p.data_type in VALID_DATA_TYPES else "string"
                self.onto.add_property(edit.name, p.name, data_type=dt, required=p.required)
            return f"Added '{edit.name}'"

        elif action == "remove_concept":
            self.onto.remove_concept(edit.name)
            return f"Removed '{edit.name}'"

        elif action == "add_relation":
            self.onto.add_relation(
                edit.name, source=edit.source, target=edit.target, cardinality=edit.cardinality
            )
            return f"Added relation '{edit.name}': {edit.source} -> {edit.target}"

        elif action == "remove_relation":
            self.onto.remove_relation(edit.name)
            return f"Removed relation '{edit.name}'"

        elif action == "add_property":
            dt = edit.data_type if edit.data_type in VALID_DATA_TYPES else "string"
            self.onto.add_property(edit.concept, edit.name, data_type=dt, required=edit.required)
            return f"Added property '{edit.name}' to '{edit.concept}'"

        elif action == "rename_concept":
            old, new = edit.old_name, edit.new_name
            if old not in self.onto.concepts:
                raise ValidationError(f"Concept '{old}' does not exist.")
            if new in self.onto.concepts:
                raise ValidationError(f"Concept '{new}' already exists.")
            concept = self.onto.concepts.pop(old)
            concept.name = new
            self.onto.concepts[new] = concept
            for c in self.onto.concepts.values():
                if c.parent == old:
                    c.parent = new
            for r in self.onto.relations.values():
                if r.source == old:
                    r.source = new
                if r.target == old:
                    r.target = new
            for inst in self.onto.instances.values():
                if inst.concept == old:
                    inst.concept = new
            return f"Renamed '{old}' -> '{new}'"

        elif action == "add_instance":
            props = dict(edit.properties) if edit.properties else {}
            self.onto.add_instance(edit.name, concept=edit.concept, properties=props)
            return f"Added instance '{edit.name}'"

        else:
            raise ValueError(f"Unknown action: {action}")

    def get_summary(self) -> str:
        """Get a formatted summary of the scenario analysis."""
        if self.onto is None:
            return "No scenario analyzed yet."

        lines = [
            f"Scenario Type: {self.scenario_type}",
            f"Ontology: {self.onto.name}",
            f"  {len(self.onto.concepts)} concepts, "
            f"{len(self.onto.relations)} relations, "
            f"{len(self.onto.instances)} instances",
        ]

        if self.constraints:
            lines.append("\nConstraints:")
            for c in self.constraints:
                lines.append(f"  - {c}")

        if self.goals:
            lines.append("\nGoals:")
            for g in self.goals:
                lines.append(f"  - {g}")

        if self.recommendations:
            lines.append("\nRecommendations:")
            for r in self.recommendations:
                lines.append(f"  - {r}")

        if self.optimization_notes:
            lines.append(f"\nOptimization: {self.optimization_notes}")

        return "\n".join(lines)
