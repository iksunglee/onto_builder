"""Main Ontology class — the primary user-facing object."""

from __future__ import annotations

from ontobuilder.core.model import Concept, Property, Relation, Instance
from ontobuilder.core.validation import (
    ValidationError,
    validate_concept_name_unique,
    validate_relation_name_unique,
    validate_parent_exists,
    validate_concept_exists,
    validate_property_type,
)


class Ontology:
    """An ontology: a collection of concepts, relations, and instances."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self.concepts: dict[str, Concept] = {}
        self.relations: dict[str, Relation] = {}
        self.instances: dict[str, Instance] = {}
        self._backend: object | None = None

    # -- Concepts --

    def add_concept(
        self,
        name: str,
        *,
        description: str = "",
        parent: str | None = None,
    ) -> Concept:
        validate_concept_name_unique(self, name)
        if parent:
            validate_parent_exists(self, parent)

        concept = Concept(name=name, description=description, parent=parent)
        self.concepts[name] = concept

        if self._backend:
            self._backend.add_node(name, type="concept", parent=parent)
            if parent:
                self._backend.add_edge(parent, name, type="is_a")
        return concept

    def remove_concept(self, name: str) -> None:
        validate_concept_exists(self, name)
        # Remove child references
        for c in self.concepts.values():
            if c.parent == name:
                c.parent = None
        # Remove relations referencing this concept
        to_remove = [
            r for r in self.relations.values()
            if r.source == name or r.target == name
        ]
        for r in to_remove:
            del self.relations[r.name]
        # Remove instances of this concept
        to_remove_inst = [i for i in self.instances.values() if i.concept == name]
        for i in to_remove_inst:
            del self.instances[i.name]

        if self._backend:
            self._backend.remove_node(name)

        del self.concepts[name]

    def add_property(
        self,
        concept_name: str,
        prop_name: str,
        *,
        data_type: str = "string",
        required: bool = False,
    ) -> Property:
        validate_concept_exists(self, concept_name)
        validate_property_type(data_type)
        prop = Property(name=prop_name, data_type=data_type, required=required)
        concept = self.concepts[concept_name]
        # Check for duplicate property name
        if any(p.name == prop_name for p in concept.properties):
            raise ValidationError(
                f"Property '{prop_name}' already exists on concept '{concept_name}'."
            )
        concept.properties.append(prop)
        return prop

    # -- Relations --

    def add_relation(
        self,
        name: str,
        *,
        source: str,
        target: str,
        cardinality: str = "many-to-many",
    ) -> Relation:
        validate_relation_name_unique(self, name)
        validate_concept_exists(self, source)
        validate_concept_exists(self, target)

        rel = Relation(name=name, source=source, target=target, cardinality=cardinality)
        self.relations[name] = rel

        if self._backend:
            self._backend.add_edge(source, target, type="relation", name=name)
        return rel

    def remove_relation(self, name: str) -> None:
        if name not in self.relations:
            raise ValidationError(f"Relation '{name}' does not exist.")
        rel = self.relations[name]
        if self._backend:
            self._backend.remove_edge(rel.source, rel.target)
        del self.relations[name]

    # -- Instances --

    def add_instance(
        self, name: str, *, concept: str, properties: dict | None = None
    ) -> Instance:
        validate_concept_exists(self, concept)
        if name in self.instances:
            raise ValidationError(f"Instance '{name}' already exists.")
        inst = Instance(name=name, concept=concept, properties=properties or {})
        self.instances[name] = inst

        if self._backend:
            self._backend.add_node(name, type="instance", concept=concept)
            self._backend.add_edge(name, concept, type="instance_of")
        return inst

    # -- Graph backend --

    def set_backend(self, backend: object) -> None:
        """Attach a graph backend and sync current data into it."""
        self._backend = backend
        # Sync existing concepts
        for c in self.concepts.values():
            backend.add_node(c.name, type="concept", parent=c.parent)
            if c.parent:
                backend.add_edge(c.parent, c.name, type="is_a")
        # Sync existing relations
        for r in self.relations.values():
            backend.add_edge(r.source, r.target, type="relation", name=r.name)
        # Sync existing instances
        for i in self.instances.values():
            backend.add_node(i.name, type="instance", concept=i.concept)
            backend.add_edge(i.name, i.concept, type="instance_of")

    # -- Display --

    def print_tree(self) -> str:
        """Return an ASCII tree of the concept hierarchy."""
        roots = [c for c in self.concepts.values() if c.parent is None]
        roots.sort(key=lambda c: c.name)
        lines: list[str] = [f"Ontology: {self.name}"]
        for i, root in enumerate(roots):
            is_last = i == len(roots) - 1
            self._print_subtree(root, lines, prefix="", is_last=is_last)
        tree = "\n".join(lines)
        return tree

    def _print_subtree(
        self, concept: Concept, lines: list[str], prefix: str, is_last: bool
    ) -> None:
        connector = "└── " if is_last else "├── "
        label = concept.name
        if concept.description:
            label += f" - {concept.description}"
        lines.append(f"{prefix}{connector}{label}")
        children = sorted(
            [c for c in self.concepts.values() if c.parent == concept.name],
            key=lambda c: c.name,
        )
        child_prefix = prefix + ("    " if is_last else "│   ")
        for j, child in enumerate(children):
            self._print_subtree(child, lines, child_prefix, j == len(children) - 1)

    # -- Serialization helpers --

    def to_dict(self) -> dict:
        data: dict = {
            "ontology": {"name": self.name},
        }
        if self.description:
            data["ontology"]["description"] = self.description
        if self.concepts:
            data["concepts"] = [c.to_dict() for c in self.concepts.values()]
        if self.relations:
            data["relations"] = [r.to_dict() for r in self.relations.values()]
        if self.instances:
            data["instances"] = [i.to_dict() for i in self.instances.values()]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Ontology:
        meta = data.get("ontology", {})
        onto = cls(name=meta.get("name", "Untitled"), description=meta.get("description", ""))

        # Load concepts in order that respects parent dependencies
        concept_dicts = data.get("concepts", [])
        loaded: set[str] = set()
        remaining = list(concept_dicts)
        max_passes = len(remaining) + 1
        while remaining and max_passes > 0:
            max_passes -= 1
            still_remaining = []
            for cd in remaining:
                parent = cd.get("parent")
                if parent and parent not in loaded:
                    still_remaining.append(cd)
                else:
                    c = Concept.from_dict(cd)
                    onto.concepts[c.name] = c
                    loaded.add(c.name)
            remaining = still_remaining

        for rd in data.get("relations", []):
            r = Relation.from_dict(rd)
            onto.relations[r.name] = r

        for id_ in data.get("instances", []):
            i = Instance.from_dict(id_)
            onto.instances[i.name] = i

        return onto

    def __repr__(self) -> str:
        return (
            f"Ontology('{self.name}', "
            f"concepts={len(self.concepts)}, "
            f"relations={len(self.relations)}, "
            f"instances={len(self.instances)})"
        )
