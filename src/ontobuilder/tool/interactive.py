"""Interactive ontology builder - the -i mode.

Guides users step-by-step through data analysis, concept creation,
relation mapping, and OWL export. Works entirely without LLM.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ontobuilder.core.model import Property
from ontobuilder.core.ontology import Ontology
from ontobuilder.tool.analyzer import DataAnalyzer, DataProfile
from ontobuilder.tool.suggestions import (
    ConceptSuggestion,
    OntologySuggestions,
    RelationSuggestion,
    SuggestionEngine,
)


class InteractiveBuilder:
    """Step-by-step guided ontology building from data."""

    def __init__(self) -> None:
        self.console = Console()
        self.analyzer = DataAnalyzer()
        self.engine = SuggestionEngine()

    def run(self, file_path: str) -> Ontology | None:
        """Run the full interactive flow. Returns built Ontology or None."""
        # Step 0: Analyze data
        self.console.print()
        profile = self._analyze(file_path)
        if profile is None:
            return None

        # Step 1: Show data overview
        self._show_overview(profile)

        # Step 2: Generate suggestions
        suggestions = self.engine.suggest(profile)
        self.console.print(
            f"\n[bold green]Generated {suggestions.summary} from analysis[/bold green]\n"
        )

        # Step 3: Review concepts
        accepted_concepts = self._review_concepts(suggestions)
        if not accepted_concepts:
            self.console.print("[yellow]No concepts accepted. Aborting.[/yellow]")
            return None

        # Step 4: Review properties on main concept
        main_concept = accepted_concepts[0]
        main_concept = self._review_properties(main_concept)
        accepted_concepts[0] = main_concept

        # Step 5: Review relations
        accepted_relations = self._review_relations(suggestions, accepted_concepts)

        # Step 6: Build ontology
        onto = self._build(profile, accepted_concepts, accepted_relations)

        # Step 7: Edit loop
        onto = self._edit_loop(onto)

        # Step 8: Show final result and export
        self._show_final(onto)

        return onto

    # ---- Step 0: Analyze ----

    def _analyze(self, file_path: str) -> DataProfile | None:
        try:
            with self.console.status("[bold blue]Analyzing data...[/bold blue]"):
                return self.analyzer.analyze(file_path)
        except (FileNotFoundError, ValueError) as e:
            self.console.print(f"[red]Error: {e}[/red]")
            return None

    # ---- Step 1: Overview ----

    def _show_overview(self, profile: DataProfile) -> None:
        table = Table(title=f"Data Analysis: {Path(profile.file_path).name}")
        table.add_column("Column", style="bold")
        table.add_column("Type", style="cyan")
        table.add_column("Unique", justify="right")
        table.add_column("Nulls", justify="right")
        table.add_column("Samples", style="dim", max_width=40)
        table.add_column("Notes")

        for col in profile.columns:
            notes = []
            if col.is_id_like:
                notes.append("[dim]ID[/dim]")
            if col.is_foreign_key:
                ref = f" -> {col.referenced_entity}" if col.referenced_entity else ""
                notes.append(f"[yellow]FK{ref}[/yellow]")
            if col.is_categorical:
                notes.append(f"[green]Categorical ({col.unique_count})[/green]")
            if col.null_rate > 0.3:
                notes.append(f"[red]{col.null_rate:.0%} null[/red]")

            # Show sample values (truncated)
            samples = ", ".join(s[:20] for s in col.sample_values[:3])
            if len(col.sample_values) > 3:
                samples += "..."

            table.add_row(
                col.name,
                col.inferred_type,
                str(col.unique_count),
                str(col.null_count),
                samples,
                " | ".join(notes) if notes else "",
            )

        self.console.print()
        self.console.print(table)
        self.console.print(
            f"\n  [dim]{profile.row_count} rows, {len(profile.columns)} columns, "
            f"suggested concept: [bold]{profile.suggested_concept_name}[/bold][/dim]"
        )

        # Show data cleaning suggestions
        if profile.cleaning_suggestions:
            self.console.print(
                Panel(
                    "[bold]Data Cleaning Suggestions[/bold]",
                    border_style="yellow",
                )
            )
            for cs in profile.cleaning_suggestions:
                self.console.print(
                    f"  [yellow]![/yellow] [bold]{cs.column}[/bold]: {cs.description}"
                )
                self.console.print(f"    → {cs.suggestion}")
                if cs.sample:
                    self.console.print(f"    [dim]e.g. {cs.sample}[/dim]")

    # ---- Step 3: Concepts ----

    def _review_concepts(self, suggestions: OntologySuggestions) -> list[ConceptSuggestion]:
        self.console.print(Panel("[bold]Step 1: Review Concepts[/bold]", border_style="blue"))
        accepted = []

        for cs in suggestions.concepts:
            source_label = {"main": "data file", "foreign_key": "foreign key", "categorical": "category", "nested": "nested object"}.get(cs.source, cs.source)

            self.console.print(f"\n  [bold]{cs.name}[/bold] [dim](from {source_label})[/dim]")
            self.console.print(f"  {cs.description}")
            if cs.properties:
                prop_names = ", ".join(p.name for p in cs.properties[:5])
                if len(cs.properties) > 5:
                    prop_names += f" (+{len(cs.properties) - 5} more)"
                self.console.print(f"  Properties: {prop_names}")

            if Confirm.ask("  Accept this concept?", default=True):
                # Allow rename
                new_name = Prompt.ask("  Name", default=cs.name)
                cs.name = new_name
                accepted.append(cs)

        return accepted

    # ---- Step 4: Properties ----

    def _review_properties(self, concept: ConceptSuggestion) -> ConceptSuggestion:
        if not concept.properties:
            return concept

        self.console.print(
            Panel(f"[bold]Step 2: Review Properties for {concept.name}[/bold]", border_style="blue")
        )

        accepted_props = []
        for prop in concept.properties:
            display = f"  {prop.name} ({prop.data_type})"
            if prop.required:
                display += " [bold red]*required[/bold red]"
            self.console.print(display)
            if Confirm.ask("  Keep?", default=True):
                accepted_props.append(prop)

        # Offer to add custom properties
        while Confirm.ask("\n  Add a custom property?", default=False):
            name = Prompt.ask("  Property name")
            dtype = Prompt.ask(
                "  Type",
                choices=["string", "int", "float", "bool", "date"],
                default="string",
            )
            req = Confirm.ask("  Required?", default=False)
            accepted_props.append(Property(name=name, data_type=dtype, required=req))

        concept.properties = accepted_props
        return concept

    # ---- Step 5: Relations ----

    def _review_relations(
        self,
        suggestions: OntologySuggestions,
        accepted_concepts: list[ConceptSuggestion],
    ) -> list[RelationSuggestion]:
        concept_names = {c.name for c in accepted_concepts}

        # Filter relations to only those connecting accepted concepts
        valid = [
            r for r in suggestions.relations
            if r.source in concept_names and r.target in concept_names
        ]

        if not valid:
            self.console.print(
                "\n[dim]No relations to suggest (only one concept accepted).[/dim]"
            )
            return []

        self.console.print(Panel("[bold]Step 3: Review Relations[/bold]", border_style="blue"))
        accepted = []

        for rs in valid:
            self.console.print(
                f"\n  [bold]{rs.source}[/bold] --[{rs.name}]--> [bold]{rs.target}[/bold] "
                f"({rs.cardinality})"
            )
            self.console.print(f"  [dim]Reason: {rs.reason}[/dim]")

            if Confirm.ask("  Accept this relation?", default=True):
                new_name = Prompt.ask("  Relation name", default=rs.name)
                rs.name = new_name
                accepted.append(rs)

        # Offer custom relations
        while Confirm.ask("\n  Add a custom relation?", default=False):
            name = Prompt.ask("  Relation name")
            source = Prompt.ask("  Source concept", choices=list(concept_names))
            target = Prompt.ask("  Target concept", choices=list(concept_names))
            card = Prompt.ask(
                "  Cardinality",
                choices=["one-to-one", "one-to-many", "many-to-one", "many-to-many"],
                default="many-to-one",
            )
            accepted.append(RelationSuggestion(
                name=name, source=source, target=target,
                cardinality=card, reason="User-defined",
            ))

        return accepted

    # ---- Step 6: Build ----

    def _build(
        self,
        profile: DataProfile,
        concepts: list[ConceptSuggestion],
        relations: list[RelationSuggestion],
    ) -> Ontology:
        onto = Ontology(profile.suggested_concept_name + "Ontology")

        for cs in concepts:
            if cs.parent and cs.parent not in onto.concepts:
                onto.add_concept(cs.parent)
            if cs.name not in onto.concepts:
                onto.add_concept(cs.name, description=cs.description, parent=cs.parent)
            for prop in cs.properties:
                onto.add_property(
                    cs.name, prop.name,
                    data_type=prop.data_type, required=prop.required,
                )

        for rs in relations:
            if rs.source in onto.concepts and rs.target in onto.concepts:
                onto.add_relation(
                    rs.name, source=rs.source, target=rs.target,
                    cardinality=rs.cardinality,
                )

        return onto

    # ---- Step 7: Edit loop ----

    def _edit_loop(self, onto: Ontology) -> Ontology:
        self.console.print(Panel("[bold]Step 4: Review & Edit[/bold]", border_style="blue"))
        self.console.print(f"\n{onto.print_tree()}")

        self.console.print(
            "\n[dim]Commands: add-concept, add-property, add-relation, remove-concept, "
            "remove-relation, tree, done[/dim]"
        )

        while True:
            try:
                cmd = Prompt.ask("\n  Command", default="done")
            except (EOFError, KeyboardInterrupt):
                break

            if cmd == "done":
                break
            elif cmd == "tree":
                self.console.print(f"\n{onto.print_tree()}")
            elif cmd == "add-concept":
                name = Prompt.ask("  Concept name")
                desc = Prompt.ask("  Description", default="")
                parent_choices = ["(none)"] + list(onto.concepts.keys())
                parent = Prompt.ask("  Parent", choices=parent_choices, default="(none)")
                onto.add_concept(name, description=desc, parent=parent if parent != "(none)" else None)
                self.console.print(f"  [green]Added concept: {name}[/green]")
            elif cmd == "add-property":
                concept_choices = list(onto.concepts.keys())
                if not concept_choices:
                    self.console.print("  [yellow]No concepts to add properties to.[/yellow]")
                    continue
                concept = Prompt.ask("  On concept", choices=concept_choices)
                name = Prompt.ask("  Property name")
                dtype = Prompt.ask("  Type", choices=["string", "int", "float", "bool", "date"], default="string")
                onto.add_property(concept, name, data_type=dtype)
                self.console.print(f"  [green]Added property: {name} ({dtype}) on {concept}[/green]")
            elif cmd == "add-relation":
                concept_choices = list(onto.concepts.keys())
                if len(concept_choices) < 2:
                    self.console.print("  [yellow]Need at least 2 concepts for a relation.[/yellow]")
                    continue
                name = Prompt.ask("  Relation name")
                source = Prompt.ask("  Source", choices=concept_choices)
                target = Prompt.ask("  Target", choices=concept_choices)
                card = Prompt.ask("  Cardinality", choices=["one-to-one", "one-to-many", "many-to-one", "many-to-many"], default="many-to-one")
                onto.add_relation(name, source=source, target=target, cardinality=card)
                self.console.print(f"  [green]Added relation: {source} --[{name}]--> {target}[/green]")
            elif cmd == "remove-concept":
                concept_choices = list(onto.concepts.keys())
                if not concept_choices:
                    self.console.print("  [yellow]No concepts to remove.[/yellow]")
                    continue
                name = Prompt.ask("  Concept to remove", choices=concept_choices)
                onto.remove_concept(name)
                self.console.print(f"  [red]Removed concept: {name}[/red]")
            elif cmd == "remove-relation":
                rel_choices = list(onto.relations.keys())
                if not rel_choices:
                    self.console.print("  [yellow]No relations to remove.[/yellow]")
                    continue
                name = Prompt.ask("  Relation to remove", choices=rel_choices)
                onto.remove_relation(name)
                self.console.print(f"  [red]Removed relation: {name}[/red]")
            else:
                self.console.print("  [dim]Unknown command. Try: add-concept, add-property, add-relation, remove-concept, remove-relation, tree, done[/dim]")

        return onto

    # ---- Step 8: Final ----

    def _show_final(self, onto: Ontology) -> None:
        # Run consistency check
        from ontobuilder.owl.reasoning import OWLReasoner

        reasoner = OWLReasoner(onto)
        result = reasoner.run_inference()

        self.console.print(
            Panel(
                f"{onto.print_tree()}\n\n"
                f"[bold]Concepts:[/bold] {len(onto.concepts)}  "
                f"[bold]Relations:[/bold] {len(onto.relations)}  "
                f"[bold]Consistent:[/bold] {'[green]Yes[/green]' if result.is_consistent else '[red]No[/red]'}",
                title=f"Final Ontology: {onto.name}",
                border_style="green" if result.is_consistent else "red",
            )
        )

        if result.consistency_issues:
            self.console.print("[yellow]Issues:[/yellow]")
            for issue in result.consistency_issues:
                self.console.print(f"  ! {issue}")

        # Show OWL preview
        from ontobuilder.owl.export import export_turtle

        turtle = export_turtle(onto)
        if len(turtle) > 2000:
            turtle = turtle[:2000] + "\n# ... (truncated)"
        self.console.print(Panel(turtle, title="OWL Turtle Preview", border_style="dim"))
