# src/ontobuilder/tool/compare.py
"""Ontology diff and merge."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ontobuilder.core.ontology import Ontology


@dataclass
class DiffSide:
    """Elements present on one side only."""

    concepts: list[str] = field(default_factory=list)
    relations: list[str] = field(default_factory=list)
    instances: list[str] = field(default_factory=list)
    scenarios: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)


@dataclass
class OntologyDiff:
    """Result of comparing two ontologies."""

    only_in_a: DiffSide = field(default_factory=DiffSide)
    only_in_b: DiffSide = field(default_factory=DiffSide)
    modified: list[dict[str, Any]] = field(default_factory=list)

    @property
    def summary(self) -> str:
        a_total = (
            len(self.only_in_a.concepts)
            + len(self.only_in_a.relations)
            + len(self.only_in_a.instances)
        )
        b_total = (
            len(self.only_in_b.concepts)
            + len(self.only_in_b.relations)
            + len(self.only_in_b.instances)
        )
        mod_total = len(self.modified)
        if a_total == 0 and b_total == 0 and mod_total == 0:
            return "Ontologies are identical"
        return (
            f"Only in A: {a_total} elements, "
            f"Only in B: {b_total} elements, "
            f"Modified: {mod_total} elements"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "only_in_a": {
                "concepts": self.only_in_a.concepts,
                "relations": self.only_in_a.relations,
                "instances": self.only_in_a.instances,
                "scenarios": self.only_in_a.scenarios,
                "constraints": self.only_in_a.constraints,
            },
            "only_in_b": {
                "concepts": self.only_in_b.concepts,
                "relations": self.only_in_b.relations,
                "instances": self.only_in_b.instances,
                "scenarios": self.only_in_b.scenarios,
                "constraints": self.only_in_b.constraints,
            },
            "modified": self.modified,
            "summary": self.summary,
        }


def diff_ontologies(a: Ontology, b: Ontology) -> OntologyDiff:
    """Compare two ontologies and return their differences."""
    result = OntologyDiff()

    # Concepts
    a_concepts = set(a.concepts.keys())
    b_concepts = set(b.concepts.keys())
    result.only_in_a.concepts = sorted(a_concepts - b_concepts)
    result.only_in_b.concepts = sorted(b_concepts - a_concepts)

    for name in sorted(a_concepts & b_concepts):
        ca = a.concepts[name]
        cb = b.concepts[name]
        diffs: dict[str, Any] = {}
        if ca.description != cb.description:
            diffs["description"] = {"a": ca.description, "b": cb.description}
        if ca.parent != cb.parent:
            diffs["parent"] = {"a": ca.parent, "b": cb.parent}
        a_props = {p.name: p for p in ca.properties}
        b_props = {p.name: p for p in cb.properties}
        if set(a_props.keys()) != set(b_props.keys()):
            diffs["properties"] = {
                "only_in_a": sorted(set(a_props) - set(b_props)),
                "only_in_b": sorted(set(b_props) - set(a_props)),
            }
        else:
            prop_diffs = []
            for pname in a_props:
                pa = a_props[pname]
                pb = b_props[pname]
                if pa.data_type != pb.data_type or pa.required != pb.required:
                    prop_diffs.append(pname)
            if prop_diffs:
                diffs["properties_changed"] = prop_diffs
        if diffs:
            result.modified.append({"name": name, "type": "concept", **diffs})

    # Relations
    a_rels = set(a.relations.keys())
    b_rels = set(b.relations.keys())
    result.only_in_a.relations = sorted(a_rels - b_rels)
    result.only_in_b.relations = sorted(b_rels - a_rels)

    for name in sorted(a_rels & b_rels):
        ra = a.relations[name]
        rb = b.relations[name]
        diffs = {}
        if ra.source != rb.source:
            diffs["source"] = {"a": ra.source, "b": rb.source}
        if ra.target != rb.target:
            diffs["target"] = {"a": ra.target, "b": rb.target}
        if ra.cardinality != rb.cardinality:
            diffs["cardinality"] = {"a": ra.cardinality, "b": rb.cardinality}
        if diffs:
            result.modified.append({"name": name, "type": "relation", **diffs})

    # Instances
    a_inst = set(a.instances.keys())
    b_inst = set(b.instances.keys())
    result.only_in_a.instances = sorted(a_inst - b_inst)
    result.only_in_b.instances = sorted(b_inst - a_inst)

    # Scenarios
    a_scen = set(a.scenarios.keys())
    b_scen = set(b.scenarios.keys())
    result.only_in_a.scenarios = sorted(a_scen - b_scen)
    result.only_in_b.scenarios = sorted(b_scen - a_scen)

    # Constraints
    a_con = set(a.constraints.keys())
    b_con = set(b.constraints.keys())
    result.only_in_a.constraints = sorted(a_con - b_con)
    result.only_in_b.constraints = sorted(b_con - a_con)

    return result


def merge_ontologies(a: Ontology, b: Ontology) -> Ontology:
    """Merge B into A: keep all of A, add elements only in B."""
    merged = Ontology.from_dict(a.to_dict())
    diff = diff_ontologies(a, b)

    # Add B-only concepts (respecting parent order)
    remaining = list(diff.only_in_b.concepts)
    max_passes = len(remaining) + 1
    while remaining and max_passes > 0:
        max_passes -= 1
        still_remaining = []
        for name in remaining:
            concept = b.concepts[name]
            if concept.parent and concept.parent not in merged.concepts:
                still_remaining.append(name)
            else:
                merged.add_concept(
                    name,
                    description=concept.description,
                    parent=concept.parent,
                )
                for prop in concept.properties:
                    merged.add_property(
                        name,
                        prop.name,
                        data_type=prop.data_type,
                        required=prop.required,
                    )
        remaining = still_remaining

    # Add B-only relations (only if both endpoints exist in merged)
    for name in diff.only_in_b.relations:
        rel = b.relations[name]
        if rel.source in merged.concepts and rel.target in merged.concepts:
            merged.add_relation(
                name,
                source=rel.source,
                target=rel.target,
                cardinality=rel.cardinality,
            )

    # Add B-only instances (only if concept exists in merged)
    for name in diff.only_in_b.instances:
        inst = b.instances[name]
        if inst.concept in merged.concepts:
            merged.add_instance(
                name,
                concept=inst.concept,
                properties=dict(inst.properties),
            )

    # Add B-only scenarios
    for name in diff.only_in_b.scenarios:
        s = b.scenarios[name]
        merged.add_scenario(
            name,
            description=s.description,
            root_concept=s.root_concept,
            includes=list(s.includes),
            action=s.action,
        )

    # Add B-only constraints
    for name in diff.only_in_b.constraints:
        c = b.constraints[name]
        merged.add_constraint(
            name,
            description=c.description,
            query=c.query,
            violation=c.violation,
        )

    return merged
