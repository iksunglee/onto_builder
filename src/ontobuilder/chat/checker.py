"""Chat-based ontology checker - ask questions about your ontology in natural language.

Works in two modes:
1. LLM-powered (requires ontobuilder[llm]) - full natural language understanding
2. Keyword-based fallback - works without LLM, pattern-matches common questions
"""

from __future__ import annotations

from ontobuilder.core.ontology import Ontology
from ontobuilder.owl.reasoning import OWLReasoner
from ontobuilder.owl.query import StructuredQuery


def _ontology_context(onto: Ontology, reasoner: OWLReasoner) -> str:
    """Build a text representation of the ontology for LLM context."""
    lines = [f"Ontology: {onto.name}"]
    if onto.description:
        lines.append(f"Description: {onto.description}")
    lines.append("")

    lines.append("## Classes (OWL Classes)")
    for name, concept in onto.concepts.items():
        parent_info = f" (subClassOf: {concept.parent})" if concept.parent else ""
        lines.append(f"- {name}{parent_info}")
        if concept.description:
            lines.append(f"  Description: {concept.description}")
        all_props = reasoner.get_all_properties(name)
        if all_props:
            for pname, info in all_props.items():
                inh = " [inherited]" if info["inherited"] else ""
                req = " [required]" if info["required"] else ""
                lines.append(f"  Property: {pname} ({info['data_type']}{req}{inh})")
    lines.append("")

    lines.append("## Object Properties (Relations)")
    for name, rel in onto.relations.items():
        lines.append(f"- {name}: {rel.source} -> {rel.target} ({rel.cardinality})")
    lines.append("")

    lines.append("## Individuals (Instances)")
    for name, inst in onto.instances.items():
        types = reasoner.classify_instance(name)
        lines.append(f"- {name} (type: {', '.join(types)})")
        for k, v in inst.properties.items():
            lines.append(f"  {k}: {v}")

    return "\n".join(lines)


_CHAT_SYSTEM = """\
You are an ontology expert assistant. The user has built an OWL ontology and wants to \
check, query, or validate it through conversation.

You have access to the full ontology structure below. Answer questions accurately based \
on the actual ontology data. When checking consistency, reference specific classes, \
properties, and relations.

If asked to validate, check for:
- Missing required properties on instances
- Orphaned concepts (no relations connecting them)
- Hierarchy issues (circular inheritance, gaps)
- Domain modeling issues (missing concepts, redundant relations)

Be specific - cite class names, property names, and relation names in your answers.

{ontology_context}
"""


class OntologyChat:
    """Interactive chat checker for ontologies."""

    def __init__(self, ontology: Ontology) -> None:
        self.onto = ontology
        self.reasoner = OWLReasoner(ontology)
        self.query_engine: StructuredQuery | None = None
        self._history: list[dict[str, str]] = []
        self._context: str | None = None

    def ask(self, question: str) -> str:
        """Ask a question about the ontology.

        Tries LLM first, falls back to keyword matching.
        """
        try:
            return self._llm_answer(question)
        except ImportError:
            # LLM not available - use keyword answer or generic fallback
            keyword_answer = self._keyword_answer(question)
            if keyword_answer:
                return keyword_answer
            return self._fallback_answer(question)
        except Exception as exc:
            # Surface runtime LLM failures while still giving a useful fallback answer.
            keyword_answer = self._keyword_answer(question)
            if keyword_answer:
                return (
                    "LLM failed at runtime, so I used ontology-based reasoning instead.\n"
                    f"Reason: {exc}\n\n"
                    f"{keyword_answer}"
                )
            return (
                "LLM failed at runtime, so I used ontology-based fallback guidance instead.\n"
                f"Reason: {exc}\n\n"
                f"{self._fallback_answer(question)}"
            )

    def infer_user_intent(self, limit: int = 5, *, include_consistency: bool = True) -> list[str]:
        """Infer likely next actions a user wants to take based on ontology state."""
        suggestions: list[str] = []

        if not self.onto.concepts:
            suggestions.append(
                "Add your first core concept (for example Product, Person, or Event)."
            )
            suggestions.append("Define 3-5 domain concepts before adding relations or instances.")
            suggestions.append("Use 'onto concept add <Name>' to start building the class model.")
            return suggestions[:limit]

        concept_names = sorted(self.onto.concepts)
        concepts_without_properties = [
            concept.name for concept in self.onto.concepts.values() if not concept.properties
        ]

        if len(self.onto.concepts) > 1 and not self.onto.relations:
            suggestions.append(
                "Add relations between your core concepts to capture how entities connect."
            )

        if concepts_without_properties:
            preview = ", ".join(concepts_without_properties[:3])
            suffix = "..." if len(concepts_without_properties) > 3 else ""
            suggestions.append(
                f"Define key properties for concepts with sparse details: {preview}{suffix}."
            )

        if any(c.parent is not None for c in self.onto.concepts.values()):
            suggestions.append(
                'Review the hierarchy with `onto chat "Show the hierarchy"` to validate inheritance.'
            )
        elif len(self.onto.concepts) > 1:
            suggestions.append(
                "Link concepts into a parent-child hierarchy where inheritance is useful."
            )

        if not self.onto.instances:
            sample = ", ".join(concept_names[:2])
            suggestions.append(
                f"Add sample instances for {sample} to validate required properties and constraints."
            )
        else:
            suggestions.append("Query and validate existing instances to check modeling quality.")
            if include_consistency:
                issues = self.reasoner.check_consistency()
                if issues:
                    suggestions.append(
                        "Run a consistency review and resolve reported ontology issues."
                    )
                else:
                    suggestions.append(
                        "Run periodic consistency checks as you expand the ontology."
                    )

        suggestions.append(
            "Export to OWL/Turtle when you are ready to integrate with semantic tooling."
        )

        deduped: list[str] = []
        for suggestion in suggestions:
            if suggestion not in deduped:
                deduped.append(suggestion)
        return deduped[:limit]

    def _llm_answer(self, question: str) -> str:
        """Use LLM for natural language answer."""
        from ontobuilder.llm.client import chat

        if not self._history:
            if self._context is None:
                self._context = _ontology_context(self.onto, self.reasoner)
            self._history.append(
                {
                    "role": "system",
                    "content": _CHAT_SYSTEM.format(ontology_context=self._context),
                }
            )

        self._history.append({"role": "user", "content": question})
        response = chat(self._history)
        self._history.append({"role": "assistant", "content": response})
        return response

    def _keyword_answer(self, question: str) -> str | None:
        """Pattern-match common questions."""
        q = question.lower().strip()

        if any(
            phrase in q
            for phrase in [
                "what should i do",
                "what do i do next",
                "what next",
                "next step",
                "next steps",
                "recommend next",
                "suggest next",
            ]
        ):
            suggestions = self.infer_user_intent(limit=5)
            lines = ["Based on this ontology, you likely want to do these next steps:"]
            lines.extend(f"  - {suggestion}" for suggestion in suggestions)
            return "\n".join(lines)

        if any(w in q for w in ["how many class", "how many concept", "count class"]):
            return f"The ontology has {len(self.onto.concepts)} classes: {', '.join(self.onto.concepts.keys())}."

        if any(w in q for w in ["how many relation", "count relation"]):
            return f"The ontology has {len(self.onto.relations)} relations: {', '.join(self.onto.relations.keys())}."

        if any(w in q for w in ["how many instance", "count instance", "how many individual"]):
            return f"The ontology has {len(self.onto.instances)} instances: {', '.join(self.onto.instances.keys())}."

        if any(w in q for w in ["consistent", "valid", "issues", "problems"]):
            issues = self.reasoner.check_consistency()
            if not issues:
                return "The ontology is consistent - no issues found."
            return "Consistency issues found:\n" + "\n".join(f"  - {i}" for i in issues)

        if any(w in q for w in ["hierarch", "tree", "structure"]):
            return self.onto.print_tree()

        if q.startswith("describe ") or q.startswith("what is "):
            name = q.replace("describe ", "").replace("what is ", "").strip().rstrip("?")
            if self.query_engine is None:
                self.query_engine = StructuredQuery(self.onto)
            # Try to find matching concept
            for cname in self.onto.concepts:
                if cname.lower() == name:
                    result = self.query_engine.describe_class(cname)
                    if result:
                        r = result.results[0]
                        lines = [f"Class: {r['name']}"]
                        lines.append(f"Description: {r['description']}")
                        lines.append(f"Parent: {r['parent']}")
                        lines.append(f"Ancestors: {r['ancestors']}")
                        lines.append(f"Descendants: {r['descendants']}")
                        lines.append(f"Own properties: {r['own_properties']}")
                        lines.append(f"Inherited properties: {r['inherited_properties']}")
                        lines.append(f"Outgoing relations: {r['outgoing_relations']}")
                        lines.append(f"Direct instances: {r['direct_instances']}")
                        return "\n".join(lines)
            return None

        if any(w in q for w in ["subclass", "child", "children"]):
            for cname in self.onto.concepts:
                if cname.lower() in q:
                    descendants = self.reasoner.get_descendants(cname)
                    if descendants:
                        return f"Subclasses of {cname}: {', '.join(descendants)}"
                    return f"{cname} has no subclasses."
            return None

        if any(w in q for w in ["parent", "superclass", "ancestor"]):
            for cname in self.onto.concepts:
                if cname.lower() in q:
                    ancestors = self.reasoner.get_ancestors(cname)
                    if ancestors:
                        return f"Ancestors of {cname}: {', '.join(ancestors)}"
                    return f"{cname} is a root class (no parents)."
            return None

        if any(w in q for w in ["propert"]):
            for cname in self.onto.concepts:
                if cname.lower() in q:
                    all_props = self.reasoner.get_all_properties(cname)
                    if all_props:
                        lines = [f"Properties of {cname}:"]
                        for pname, info in all_props.items():
                            inh = " [inherited]" if info["inherited"] else ""
                            req = " [required]" if info["required"] else ""
                            lines.append(f"  - {pname}: {info['data_type']}{req}{inh}")
                        return "\n".join(lines)
                    return f"{cname} has no properties."
            return None

        if any(w in q for w in ["summary", "overview", "tell me about"]):
            inference = self.reasoner.run_inference()
            return inference.summary

        return None

    def _fallback_answer(self, _question: str) -> str:
        """Generic fallback when no pattern matches and LLM is unavailable."""
        suggestions = self.infer_user_intent(limit=3, include_consistency=False)
        suggestion_lines = "\n".join(f"  - {suggestion}" for suggestion in suggestions)
        return (
            f"I can answer questions about your ontology '{self.onto.name}'.\n"
            f"It has {len(self.onto.concepts)} classes, "
            f"{len(self.onto.relations)} relations, "
            f"and {len(self.onto.instances)} instances.\n\n"
            f"Likely next actions:\n{suggestion_lines}\n\n"
            "Try asking:\n"
            "  - 'Is the ontology consistent?'\n"
            "  - 'How many classes are there?'\n"
            "  - 'Describe <ClassName>'\n"
            "  - 'What are the subclasses of <ClassName>?'\n"
            "  - 'Show the hierarchy'\n"
            "  - 'Give me a summary'\n\n"
            "For full natural language support, install LLM deps: pip install ontobuilder[llm]"
        )

    def reset(self) -> None:
        """Reset conversation history."""
        self._history = []
