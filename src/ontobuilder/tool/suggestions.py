"""Generate ontology suggestions from data analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field

from ontobuilder.core.model import Property
from ontobuilder.core.ontology import Ontology
from ontobuilder.tool.analyzer import DataProfile


@dataclass
class ConceptSuggestion:
    """A suggested concept with rationale."""

    name: str
    description: str
    source: str  # "main", "foreign_key", "categorical", "nested"
    properties: list[Property] = field(default_factory=list)
    parent: str | None = None


@dataclass
class RelationSuggestion:
    """A suggested relation with rationale."""

    name: str
    source: str
    target: str
    cardinality: str
    reason: str  # human-readable explanation


@dataclass
class OntologySuggestions:
    """Complete set of suggestions generated from data analysis."""

    concepts: list[ConceptSuggestion] = field(default_factory=list)
    relations: list[RelationSuggestion] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        parts = [f"{len(self.concepts)} concepts, {len(self.relations)} relations"]
        if self.notes:
            parts.append(f"{len(self.notes)} notes")
        return ", ".join(parts)


class SuggestionEngine:
    """Generate ontology structure suggestions from a DataProfile."""

    def suggest(self, profile: DataProfile) -> OntologySuggestions:
        """Analyze a DataProfile and return ontology suggestions."""
        suggestions = OntologySuggestions()

        # 1. Main concept from the data source
        main = self._main_concept(profile)
        suggestions.concepts.append(main)

        # 2. Concepts from foreign keys
        fk_concepts = self._fk_concepts(profile, main.name)
        suggestions.concepts.extend(fk_concepts)

        # 3. Concepts from categorical columns (optional hierarchy)
        cat_concepts = self._categorical_concepts(profile, main.name)
        suggestions.concepts.extend(cat_concepts)

        # 4. Concepts from nested JSON objects
        nested_concepts = self._nested_concepts(profile, main.name)
        suggestions.concepts.extend(nested_concepts)

        # 5. Relations
        suggestions.relations = self._suggest_relations(
            profile, main.name, fk_concepts, cat_concepts, nested_concepts
        )

        # 6. Notes
        suggestions.notes = self._generate_notes(profile)

        return suggestions

    def build_ontology(
        self,
        suggestions: OntologySuggestions,
        name: str,
        *,
        accepted_concepts: list[str] | None = None,
        accepted_relations: list[str] | None = None,
    ) -> Ontology:
        """Build an Ontology from accepted suggestions."""
        onto = Ontology(name)

        for cs in suggestions.concepts:
            if accepted_concepts is not None and cs.name not in accepted_concepts:
                continue
            # Add parent first if needed
            if cs.parent and cs.parent not in onto.concepts:
                onto.add_concept(cs.parent)
            onto.add_concept(cs.name, description=cs.description, parent=cs.parent)
            for prop in cs.properties:
                onto.add_property(cs.name, prop.name, data_type=prop.data_type, required=prop.required)

        for rs in suggestions.relations:
            if accepted_relations is not None and rs.name not in accepted_relations:
                continue
            # Only add if both endpoints exist
            if rs.source in onto.concepts and rs.target in onto.concepts:
                onto.add_relation(rs.name, source=rs.source, target=rs.target, cardinality=rs.cardinality)

        return onto

    # ---- internal suggestion generators ----

    def _main_concept(self, profile: DataProfile) -> ConceptSuggestion:
        """Build the main concept from property columns."""
        props = []
        for col in profile.property_columns:
            if not col.is_categorical:
                props.append(Property(
                    name=col.name,
                    data_type=col.inferred_type,
                    required=(col.null_count == 0),
                ))
        return ConceptSuggestion(
            name=profile.suggested_concept_name,
            description=f"Derived from {profile.file_type.upper()} data ({profile.row_count} records)",
            source="main",
            properties=props,
        )

    def _fk_concepts(self, profile: DataProfile, main_name: str) -> list[ConceptSuggestion]:
        """Create concept stubs for each foreign key reference."""
        concepts = []
        seen = set()
        for col in profile.fk_columns:
            entity = col.referenced_entity
            if entity and entity != main_name and entity not in seen:
                seen.add(entity)
                concepts.append(ConceptSuggestion(
                    name=entity,
                    description=f"Referenced entity (via {col.name})",
                    source="foreign_key",
                ))
        return concepts

    def _categorical_concepts(self, profile: DataProfile, main_name: str) -> list[ConceptSuggestion]:
        """Create concepts from categorical columns with few unique values."""
        concepts = []
        for col in profile.categorical_columns:
            concept_name = _col_to_concept_name(col.name)
            if concept_name == main_name:
                continue
            desc = f"Category with {col.unique_count} values: {', '.join(col.categories[:5])}"
            if len(col.categories) > 5:
                desc += f" (+{len(col.categories) - 5} more)"
            concepts.append(ConceptSuggestion(
                name=concept_name,
                description=desc,
                source="categorical",
            ))
        return concepts

    def _nested_concepts(self, profile: DataProfile, main_name: str) -> list[ConceptSuggestion]:
        """Create concepts from nested JSON objects."""
        concepts = []
        for nested in profile.nested_objects:
            name = _col_to_concept_name(nested["parent_key"])
            if name == main_name:
                continue
            if nested.get("is_array"):
                desc = f"Nested array in {main_name}"
            else:
                keys = nested.get("keys", [])
                desc = f"Nested object with fields: {', '.join(keys[:5])}"
            concepts.append(ConceptSuggestion(
                name=name,
                description=desc,
                source="nested",
            ))
        return concepts

    def _suggest_relations(
        self,
        profile: DataProfile,
        main_name: str,
        fk_concepts: list[ConceptSuggestion],
        cat_concepts: list[ConceptSuggestion],
        nested_concepts: list[ConceptSuggestion],
    ) -> list[RelationSuggestion]:
        """Generate relation suggestions."""
        relations = []

        # FK relations: main → referenced entity
        for col in profile.fk_columns:
            entity = col.referenced_entity
            if entity and entity != main_name:
                # Determine cardinality from uniqueness
                if col.uniqueness_ratio > 0.95:
                    card = "one-to-one"
                else:
                    card = "many-to-one"
                rel_name = f"has_{entity.lower()}"
                relations.append(RelationSuggestion(
                    name=rel_name,
                    source=main_name,
                    target=entity,
                    cardinality=card,
                    reason=f"Foreign key column '{col.name}'",
                ))

        # Categorical relations: main → category
        for cs in cat_concepts:
            rel_name = f"has_{cs.name.lower()}"
            relations.append(RelationSuggestion(
                name=rel_name,
                source=main_name,
                target=cs.name,
                cardinality="many-to-one",
                reason=f"Categorical column with {len([c for c in profile.columns if _col_to_concept_name(c.name) == cs.name][0].categories if [c for c in profile.columns if _col_to_concept_name(c.name) == cs.name] else [])} values",
            ))

        # Nested object relations
        for ns in nested_concepts:
            is_array = any(
                n.get("is_array") for n in profile.nested_objects
                if _col_to_concept_name(n["parent_key"]) == ns.name
            )
            rel_name = f"has_{ns.name.lower()}"
            relations.append(RelationSuggestion(
                name=rel_name,
                source=main_name,
                target=ns.name,
                cardinality="one-to-many" if is_array else "one-to-one",
                reason=f"Nested {'array' if is_array else 'object'} in JSON",
            ))

        return relations

    def _generate_notes(self, profile: DataProfile) -> list[str]:
        """Generate helpful notes about the data."""
        notes = []

        # High null columns
        high_null = [c for c in profile.columns if c.null_rate > 0.3]
        if high_null:
            names = ", ".join(c.name for c in high_null)
            notes.append(f"Columns with >30% nulls (consider optional): {names}")

        # Potential composite keys
        high_unique = [
            c for c in profile.columns
            if c.inferred_type == "string" and c.uniqueness_ratio > 0.9 and not c.is_id_like
        ]
        if high_unique:
            names = ", ".join(c.name for c in high_unique)
            notes.append(f"High-uniqueness string columns (possible identifiers): {names}")

        if not profile.fk_columns and not profile.nested_objects:
            notes.append("No foreign keys or nested objects detected - this may be a flat dataset")

        return notes


def _col_to_concept_name(col_name: str) -> str:
    """Convert column name to PascalCase concept name."""
    import re
    parts = re.split(r"[_\-\s]+", col_name.strip())
    result = []
    for p in parts:
        word = p.capitalize()
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        result.append(word)
    return "".join(result) if result else "Thing"
