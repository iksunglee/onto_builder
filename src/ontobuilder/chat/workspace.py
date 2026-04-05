"""Ontology Workspace - data-first workflow with chat-driven refinement.

Flow:
1. Analyze data file with LLM -> generate base ontology
2. Enter interactive chat session
3. User asks questions, requests changes, the LLM returns structured edits
4. Edits are applied to the live ontology
5. Export to OWL at any time
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ontobuilder.core.ontology import Ontology
from ontobuilder.core.validation import ValidationError
from ontobuilder.owl.reasoning import OWLReasoner
from ontobuilder.owl.export import export_turtle


_WORKSPACE_SYSTEM = """\
You are an OWL ontology architect working in a live editing session. The user has an \
ontology that was auto-generated from data analysis. Your job is to help them understand, \
validate, and refine it through conversation.

CURRENT ONTOLOGY STATE:
{ontology_state}

You can do two things:
1. ANSWER questions about the ontology (explain structure, check consistency, suggest improvements)
2. MAKE CHANGES by returning edit commands in the `edits` field

Available edit commands:
- add_concept: Add a new OWL class (with optional parent and properties)
- remove_concept: Remove a class and its dependents
- add_relation: Add an OWL ObjectProperty between two classes
- remove_relation: Remove a relation
- add_property: Add a DatatypeProperty to a class
- rename_concept: Rename a class (updates all references)
- add_instance: Add a NamedIndividual

RULES:
- Always explain what you're doing in the `explanation` field
- Only make changes the user asked for or confirmed
- When suggesting improvements, explain why before applying
- Validate that parent classes exist before adding subclasses
- Use proper data types: string, int, float, bool, date
- Keep the ontology clean - no orphans, no redundancies
- If the user asks to "check" or "validate", run through consistency issues
- If the user says "show" or "export", describe the current state
"""


def _serialize_ontology_state(onto: Ontology) -> str:
    """Serialize ontology to a compact text format for LLM context."""
    reasoner = OWLReasoner(onto)
    lines = [f"Name: {onto.name}"]
    if onto.description:
        lines.append(f"Description: {onto.description}")
    lines.append(f"Classes: {len(onto.concepts)}")
    lines.append(f"Relations: {len(onto.relations)}")
    lines.append(f"Instances: {len(onto.instances)}")
    lines.append("")

    lines.append("## OWL Classes")
    for name, concept in onto.concepts.items():
        parent_info = f" rdfs:subClassOf {concept.parent}" if concept.parent else ""
        lines.append(f"  owl:Class {name}{parent_info}")
        if concept.description:
            lines.append(f'    rdfs:comment "{concept.description}"')
        all_props = reasoner.get_all_properties(name)
        for pname, info in all_props.items():
            inh = " [inherited]" if info["inherited"] else ""
            req = " [required]" if info["required"] else ""
            lines.append(f"    owl:DatatypeProperty {pname} : {info['data_type']}{req}{inh}")

    lines.append("")
    lines.append("## OWL ObjectProperties (Relations)")
    for name, rel in onto.relations.items():
        lines.append(f"  owl:ObjectProperty {name}")
        lines.append(f"    rdfs:domain {rel.source}")
        lines.append(f"    rdfs:range {rel.target}")
        lines.append(f"    cardinality: {rel.cardinality}")

    lines.append("")
    lines.append("## OWL NamedIndividuals")
    for name, inst in onto.instances.items():
        types = reasoner.classify_instance(name)
        lines.append(f"  owl:NamedIndividual {name} rdf:type {', '.join(types)}")
        for k, v in inst.properties.items():
            lines.append(f"    {k} = {v!r}")

    # Consistency check
    issues = reasoner.check_consistency()
    if issues:
        lines.append("")
        lines.append("## Known Issues")
        for issue in issues:
            lines.append(f"  - {issue}")

    return "\n".join(lines)


class OntologyWorkspace:
    """Live ontology editing workspace with LLM-powered chat."""

    def __init__(self, ontology: Ontology) -> None:
        self.onto = ontology
        self._history: list[dict[str, str]] = []
        self._edit_log: list[dict[str, Any]] = []

    @classmethod
    def from_data(cls, file_path: str | Path, max_rows: int = 30) -> OntologyWorkspace:
        """Create a workspace by analyzing a data file with LLM.

        Reads the data, sends it to the LLM for inference, builds the
        base ontology, and returns a workspace ready for chat refinement.
        """
        from ontobuilder.llm.inference import read_sample_data
        from ontobuilder.llm.client import chat
        from ontobuilder.llm.schemas import OntologySuggestion
        from ontobuilder.llm.prompts import infer_prompt

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")

        sample = read_sample_data(path, max_rows=max_rows)
        suggestion: OntologySuggestion = chat(
            infer_prompt(sample),
            response_model=OntologySuggestion,
        )

        onto = _build_ontology_from_suggestion(suggestion)
        workspace = cls(onto)
        workspace._edit_log.append(
            {
                "action": "init_from_data",
                "source": str(path),
                "concepts": len(onto.concepts),
                "relations": len(onto.relations),
            }
        )
        return workspace

    @classmethod
    def from_existing(cls, ontology: Ontology) -> OntologyWorkspace:
        """Create a workspace from an existing ontology."""
        return cls(ontology)

    def ask(self, message: str) -> dict[str, Any]:
        """Send a message and get structured response with optional edits.

        Returns:
            Dict with keys:
            - ``explanation``: str - LLM's explanation
            - ``edits_applied``: list[str] - descriptions of applied edits
            - ``errors``: list[str] - any edit errors
            - ``ontology_state``: str - current ontology summary after changes
        """
        from ontobuilder.llm.client import chat
        from ontobuilder.llm.schemas import WorkspaceResponse

        # Refresh ontology state in system prompt each turn
        state = _serialize_ontology_state(self.onto)
        system_msg = _WORKSPACE_SYSTEM.format(ontology_state=state)

        # Build messages: system + history + new message
        messages = [{"role": "system", "content": system_msg}]
        messages.extend(self._history)
        messages.append({"role": "user", "content": message})

        response: WorkspaceResponse = chat(messages, response_model=WorkspaceResponse)

        # Apply edits
        edits_applied = []
        errors = []
        for edit in response.edits:
            try:
                desc = self._apply_edit(edit)
                edits_applied.append(desc)
            except (ValidationError, Exception) as e:
                errors.append(f"{edit.action}: {e}")

        # Update history (keep it compact)
        self._history.append({"role": "user", "content": message})
        edit_summary = ""
        if edits_applied:
            edit_summary = "\n[Applied: " + ", ".join(edits_applied) + "]"
        self._history.append(
            {
                "role": "assistant",
                "content": response.explanation + edit_summary,
            }
        )

        # Trim history to last 20 turns to avoid token overflow
        if len(self._history) > 40:
            self._history = self._history[-20:]

        return {
            "explanation": response.explanation,
            "edits_applied": edits_applied,
            "errors": errors,
            "ontology_state": f"{len(self.onto.concepts)} classes, "
            f"{len(self.onto.relations)} relations, "
            f"{len(self.onto.instances)} instances",
        }

    def _apply_edit(self, edit) -> str:
        """Apply a single edit command to the ontology. Returns description."""
        action = edit.action

        if action == "add_concept":
            parent = edit.parent if edit.parent and edit.parent in self.onto.concepts else None
            self.onto.add_concept(edit.name, description=edit.description, parent=parent)
            for p in edit.properties:
                dt = (
                    p.data_type
                    if p.data_type in {"string", "int", "float", "bool", "date"}
                    else "string"
                )
                self.onto.add_property(edit.name, p.name, data_type=dt, required=p.required)
            self._edit_log.append({"action": "add_concept", "name": edit.name})
            return f"Added class '{edit.name}'"

        elif action == "remove_concept":
            self.onto.remove_concept(edit.name)
            self._edit_log.append({"action": "remove_concept", "name": edit.name})
            return f"Removed class '{edit.name}'"

        elif action == "add_relation":
            card = (
                edit.cardinality
                if edit.cardinality in {"one-to-one", "one-to-many", "many-to-one", "many-to-many"}
                else "many-to-many"
            )
            self.onto.add_relation(
                edit.name, source=edit.source, target=edit.target, cardinality=card
            )
            self._edit_log.append({"action": "add_relation", "name": edit.name})
            return f"Added relation '{edit.name}': {edit.source} -> {edit.target}"

        elif action == "remove_relation":
            self.onto.remove_relation(edit.name)
            self._edit_log.append({"action": "remove_relation", "name": edit.name})
            return f"Removed relation '{edit.name}'"

        elif action == "add_property":
            dt = (
                edit.data_type
                if edit.data_type in {"string", "int", "float", "bool", "date"}
                else "string"
            )
            self.onto.add_property(edit.concept, edit.name, data_type=dt, required=edit.required)
            self._edit_log.append(
                {"action": "add_property", "concept": edit.concept, "name": edit.name}
            )
            return f"Added property '{edit.name}' to '{edit.concept}'"

        elif action == "rename_concept":
            self._rename_concept(edit.old_name, edit.new_name)
            self._edit_log.append(
                {"action": "rename_concept", "old": edit.old_name, "new": edit.new_name}
            )
            return f"Renamed '{edit.old_name}' -> '{edit.new_name}'"

        elif action == "add_instance":
            props = dict(edit.properties) if edit.properties else {}
            self.onto.add_instance(edit.name, concept=edit.concept, properties=props)
            self._edit_log.append({"action": "add_instance", "name": edit.name})
            return f"Added instance '{edit.name}' of '{edit.concept}'"

        else:
            raise ValueError(f"Unknown action: {action}")

    def _rename_concept(self, old_name: str, new_name: str) -> None:
        """Rename a concept and update all references."""
        if old_name not in self.onto.concepts:
            raise ValidationError(f"Concept '{old_name}' does not exist.")
        if new_name in self.onto.concepts:
            raise ValidationError(f"Concept '{new_name}' already exists.")

        concept = self.onto.concepts.pop(old_name)
        concept.name = new_name
        self.onto.concepts[new_name] = concept

        # Update children
        for c in self.onto.concepts.values():
            if c.parent == old_name:
                c.parent = new_name

        # Update relations
        for r in self.onto.relations.values():
            if r.source == old_name:
                r.source = new_name
            if r.target == old_name:
                r.target = new_name

        # Update instances
        for inst in self.onto.instances.values():
            if inst.concept == old_name:
                inst.concept = new_name

    def get_state(self) -> str:
        """Get current ontology state as text."""
        return _serialize_ontology_state(self.onto)

    def get_edit_log(self) -> list[dict[str, Any]]:
        """Get full edit history."""
        return list(self._edit_log)

    def export_owl(self, fmt: str = "turtle") -> str:
        """Export current ontology as OWL string."""
        if fmt == "turtle":
            return export_turtle(self.onto)
        from ontobuilder.owl.export import export_owl_xml

        return export_owl_xml(self.onto)

    def save_owl(self, path: str | Path, fmt: str = "turtle") -> Path:
        """Save current ontology as OWL file."""
        from ontobuilder.owl.export import save_owl

        return save_owl(self.onto, path, fmt=fmt)

    def run_inference(self) -> str:
        """Run inference and return summary."""
        reasoner = OWLReasoner(self.onto)
        result = reasoner.run_inference()
        return result.summary


def _build_ontology_from_suggestion(suggestion) -> Ontology:
    """Build an Ontology from an OntologySuggestion."""
    onto = Ontology(suggestion.name, description=suggestion.description)

    added: set[str] = set()
    remaining = list(suggestion.concepts)
    max_passes = len(remaining) + 1
    while remaining and max_passes > 0:
        max_passes -= 1
        still_remaining = []
        for c in remaining:
            if c.parent and c.parent not in added:
                still_remaining.append(c)
            else:
                parent = c.parent if c.parent and c.parent in added else None
                onto.add_concept(c.name, description=c.description, parent=parent)
                for p in c.properties:
                    dt = (
                        p.data_type
                        if p.data_type in {"string", "int", "float", "bool", "date"}
                        else "string"
                    )
                    onto.add_property(c.name, p.name, data_type=dt, required=p.required)
                added.add(c.name)
        remaining = still_remaining

    for r in suggestion.relations:
        if r.source in added and r.target in added:
            card = (
                r.cardinality
                if r.cardinality in {"one-to-one", "one-to-many", "many-to-one", "many-to-many"}
                else "many-to-many"
            )
            onto.add_relation(r.name, source=r.source, target=r.target, cardinality=card)

    return onto
