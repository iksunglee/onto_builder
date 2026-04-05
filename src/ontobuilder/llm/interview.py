"""Interactive interview engine for building ontologies with LLM assistance."""

from __future__ import annotations

from ontobuilder.core.ontology import Ontology
from ontobuilder.llm.client import chat
from ontobuilder.llm.inference import build_ontology_from_suggestion
from ontobuilder.llm.schemas import (
    InterviewQuestions,
    OntologySuggestion,
    ConceptSuggestion,
    RelationSuggestion,
)
from ontobuilder.llm.prompts import (
    interview_scoping_prompt,
    interview_concepts_prompt,
    interview_relations_prompt,
    SYSTEM_PROMPT,
)


def run_interview(domain_hints: dict | None = None) -> Ontology | None:
    """Run an interactive interview to build an ontology.

    Returns the built Ontology, or None if the user cancels.
    """
    from rich import print as rprint
    from rich.prompt import Prompt, Confirm

    rprint("\n[bold]Welcome to the OntoBuilder Interview![/bold]")
    rprint("I'll ask you a few questions to understand your domain, then suggest an ontology.\n")

    # Step 1: Scoping questions
    rprint("[bold]Step 1: Understanding your domain[/bold]\n")
    messages = interview_scoping_prompt(domain_hints)
    questions: InterviewQuestions = chat(messages, response_model=InterviewQuestions)

    answers: list[str] = []
    for q in questions.questions:
        rprint(f"[bold cyan]Q:[/bold cyan] {q.question}")
        answer = Prompt.ask("[bold green]A[/bold green]")
        if answer.lower() in ("quit", "exit", "q"):
            rprint("Interview cancelled.")
            return None
        answers.append(f"Q: {q.question}\nA: {answer}")

    context = "\n\n".join(answers)

    # Step 2: Suggest concepts
    rprint("\n[bold]Step 2: Suggesting concepts[/bold]\n")
    rprint("Thinking...")
    suggestion: OntologySuggestion = chat(
        interview_concepts_prompt(context),
        response_model=OntologySuggestion,
    )

    rprint(f"\n[bold]Suggested ontology: {suggestion.name}[/bold]")
    if suggestion.description:
        rprint(f"  {suggestion.description}\n")

    confirmed_concepts: list[ConceptSuggestion] = []
    for concept in suggestion.concepts:
        desc = f" — {concept.description}" if concept.description else ""
        parent = f" (child of {concept.parent})" if concept.parent else ""
        props = ", ".join(p.name for p in concept.properties)
        props_str = f" [properties: {props}]" if props else ""

        rprint(f"\n  [bold]{concept.name}[/bold]{desc}{parent}{props_str}")
        if Confirm.ask("    Include this concept?", default=True):
            confirmed_concepts.append(concept)

    if not confirmed_concepts:
        rprint("No concepts confirmed. Aborting.")
        return None

    # Step 3: Suggest relations
    rprint("\n[bold]Step 3: Suggesting relations[/bold]\n")
    concept_names = [c.name for c in confirmed_concepts]
    rel_messages = interview_relations_prompt(context, concept_names)

    rel_suggestion: OntologySuggestion = chat(
        rel_messages,
        response_model=OntologySuggestion,
    )

    confirmed_relations: list[RelationSuggestion] = []
    for rel in rel_suggestion.relations:
        # Only show relations where both concepts were confirmed
        if rel.source in concept_names and rel.target in concept_names:
            rprint(f"\n  [bold]{rel.name}[/bold]: {rel.source} → {rel.target}")
            if Confirm.ask("    Include this relation?", default=True):
                confirmed_relations.append(rel)

    # Step 4: Build the ontology
    rprint("\n[bold]Step 4: Building your ontology[/bold]\n")
    onto = build_ontology_from_suggestion(
        OntologySuggestion(
            name=suggestion.name,
            description=suggestion.description,
            concepts=confirmed_concepts,
            relations=confirmed_relations,
        )
    )

    rprint("\n[bold green]Ontology built successfully![/bold green]\n")
    rprint(onto.print_tree())
    rprint(f"\n{onto}")

    return onto
