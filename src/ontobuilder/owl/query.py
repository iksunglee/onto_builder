"""Structured query engine for ontologies.

Provides programmatic, SPARQL-inspired queries without requiring
a triple store — works directly on the Ontology data model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ontobuilder.core.ontology import Ontology
from ontobuilder.owl.reasoning import OWLReasoner


@dataclass
class QueryResult:
    """Container for query results."""

    query: str
    results: list[dict[str, Any]] = field(default_factory=list)
    count: int = 0

    def __bool__(self) -> bool:
        return self.count > 0

    def to_table(self) -> str:
        """Format results as an ASCII table."""
        if not self.results:
            return f"Query: {self.query}\n(no results)"
        keys = list(self.results[0].keys())
        widths = {k: max(len(k), max(len(str(r.get(k, ""))) for r in self.results)) for k in keys}
        header = " | ".join(k.ljust(widths[k]) for k in keys)
        sep = "-+-".join("-" * widths[k] for k in keys)
        rows = []
        for r in self.results:
            rows.append(" | ".join(str(r.get(k, "")).ljust(widths[k]) for k in keys))
        return f"Query: {self.query}\n{header}\n{sep}\n" + "\n".join(rows)


class StructuredQuery:
    """Structured query engine for ontologies."""

    def __init__(self, ontology: Ontology) -> None:
        self.onto = ontology
        self.reasoner = OWLReasoner(ontology)

    def find_classes(
        self,
        *,
        parent: str | None = None,
        has_property: str | None = None,
        name_contains: str | None = None,
    ) -> QueryResult:
        """Find classes matching criteria.

        Args:
            parent: Filter by parent class (direct or transitive).
            has_property: Filter by property name (direct or inherited).
            name_contains: Filter by substring in class name (case-insensitive).
        """
        results = []
        for name, concept in self.onto.concepts.items():
            if name_contains and name_contains.lower() not in name.lower():
                continue
            if parent:
                if not self.reasoner.is_subclass_of(name, parent):
                    continue
            if has_property:
                all_props = self.reasoner.get_all_properties(name)
                if has_property not in all_props:
                    continue

            results.append({
                "class": name,
                "parent": concept.parent or "(root)",
                "description": concept.description or "",
                "properties": len(concept.properties),
            })

        return QueryResult(
            query=f"find_classes(parent={parent}, has_property={has_property}, name_contains={name_contains})",
            results=results,
            count=len(results),
        )

    def find_instances(
        self,
        *,
        of_class: str | None = None,
        include_subclasses: bool = True,
        where: dict[str, Any] | None = None,
    ) -> QueryResult:
        """Find instances matching criteria.

        Args:
            of_class: Filter by class (optionally including subclass instances).
            include_subclasses: Whether to include instances of subclasses.
            where: Dict of property_name → value filters.
        """
        results = []
        for name, inst in self.onto.instances.items():
            if of_class:
                if include_subclasses:
                    types = self.reasoner.classify_instance(name)
                    if of_class not in types:
                        continue
                else:
                    if inst.concept != of_class:
                        continue
            if where:
                match = True
                for k, v in where.items():
                    if inst.properties.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            results.append({
                "instance": name,
                "class": inst.concept,
                "properties": str(inst.properties) if inst.properties else "{}",
            })

        return QueryResult(
            query=f"find_instances(of_class={of_class}, include_subclasses={include_subclasses})",
            results=results,
            count=len(results),
        )

    def find_relations(
        self,
        *,
        source: str | None = None,
        target: str | None = None,
        name_contains: str | None = None,
    ) -> QueryResult:
        """Find relations matching criteria."""
        results = []
        for name, rel in self.onto.relations.items():
            if source and rel.source != source:
                continue
            if target and rel.target != target:
                continue
            if name_contains and name_contains.lower() not in name.lower():
                continue

            results.append({
                "relation": name,
                "source": rel.source,
                "target": rel.target,
                "cardinality": rel.cardinality,
            })

        return QueryResult(
            query=f"find_relations(source={source}, target={target})",
            results=results,
            count=len(results),
        )

    def find_path(self, from_class: str, to_class: str) -> QueryResult:
        """Find relationship paths between two classes.

        Searches through both hierarchy (is-a) and relations.
        """
        paths = []
        visited = set()

        def _dfs(current: str, target: str, path: list[str]) -> None:
            if current == target:
                paths.append(list(path))
                return
            if current in visited:
                return
            visited.add(current)

            # Try parent (is-a)
            concept = self.onto.concepts.get(current)
            if concept and concept.parent:
                _dfs(concept.parent, target, path + [f"--[is-a]--> {concept.parent}"])

            # Try children
            for name, c in self.onto.concepts.items():
                if c.parent == current:
                    _dfs(name, target, path + [f"<--[is-a]-- {name}"])

            # Try relations
            for rel in self.onto.relations.values():
                if rel.source == current:
                    _dfs(rel.target, target, path + [f"--[{rel.name}]--> {rel.target}"])
                if rel.target == current:
                    _dfs(rel.source, target, path + [f"<--[{rel.name}]-- {rel.source}"])

            visited.discard(current)

        _dfs(from_class, to_class, [from_class])

        results = [
            {"path": " ".join(p), "length": len(p) - 1}
            for p in sorted(paths, key=len)[:10]  # Top 10 shortest
        ]

        return QueryResult(
            query=f"find_path({from_class} → {to_class})",
            results=results,
            count=len(results),
        )

    def describe_class(self, class_name: str) -> QueryResult:
        """Get full description of a class: properties, relations, instances, hierarchy."""
        concept = self.onto.concepts.get(class_name)
        if not concept:
            return QueryResult(query=f"describe_class({class_name})", results=[], count=0)

        all_props = self.reasoner.get_all_properties(class_name)
        ancestors = self.reasoner.get_ancestors(class_name)
        descendants = self.reasoner.get_descendants(class_name)
        instances = self.reasoner.find_instances_of(class_name, include_subclasses=False)
        all_instances = self.reasoner.find_instances_of(class_name, include_subclasses=True)

        outgoing = [r for r in self.onto.relations.values() if r.source == class_name]
        incoming = [r for r in self.onto.relations.values() if r.target == class_name]

        results = [{
            "name": class_name,
            "description": concept.description or "(none)",
            "parent": concept.parent or "(root)",
            "ancestors": ", ".join(ancestors) if ancestors else "(none)",
            "descendants": ", ".join(descendants) if descendants else "(none)",
            "own_properties": ", ".join(p.name for p in concept.properties) or "(none)",
            "inherited_properties": ", ".join(
                f"{k} (from {v['defined_on']})"
                for k, v in all_props.items() if v["inherited"]
            ) or "(none)",
            "outgoing_relations": ", ".join(f"{r.name} → {r.target}" for r in outgoing) or "(none)",
            "incoming_relations": ", ".join(f"{r.source} → {r.name}" for r in incoming) or "(none)",
            "direct_instances": ", ".join(instances) or "(none)",
            "all_instances": ", ".join(all_instances) or "(none)",
        }]

        return QueryResult(
            query=f"describe_class({class_name})",
            results=results,
            count=1,
        )

    def validate_instance(self, instance_name: str) -> QueryResult:
        """Validate an instance against its class schema."""
        inst = self.onto.instances.get(instance_name)
        if not inst:
            return QueryResult(query=f"validate_instance({instance_name})", results=[], count=0)

        all_props = self.reasoner.get_all_properties(inst.concept)
        issues = []

        # Check required properties
        for prop_name, info in all_props.items():
            if info["required"] and prop_name not in inst.properties:
                issues.append(f"Missing required property: {prop_name}")

        # Check for unknown properties
        for prop_name in inst.properties:
            if prop_name not in all_props:
                issues.append(f"Unknown property: {prop_name}")

        types = self.reasoner.classify_instance(instance_name)
        status = "VALID" if not issues else "INVALID"

        results = [{
            "instance": instance_name,
            "class": inst.concept,
            "inferred_types": ", ".join(types),
            "status": status,
            "issues": "; ".join(issues) if issues else "(none)",
        }]

        return QueryResult(
            query=f"validate_instance({instance_name})",
            results=results,
            count=1,
        )
