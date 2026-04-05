"""OWL reasoning engine — inference over ontology structure.

Performs structural reasoning without a full DL reasoner:
- Subclass inference (transitive hierarchy)
- Property inheritance (inherited properties from ancestors)
- Instance classification (what classes does an instance belong to)
- Consistency checking (detect contradictions and issues)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ontobuilder.core.ontology import Ontology


@dataclass
class InferenceResult:
    """Container for reasoning results."""

    inferred_subclasses: dict[str, list[str]] = field(default_factory=dict)
    inherited_properties: dict[str, list[str]] = field(default_factory=dict)
    instance_types: dict[str, list[str]] = field(default_factory=dict)
    consistency_issues: list[str] = field(default_factory=list)
    summary: str = ""

    @property
    def is_consistent(self) -> bool:
        return len(self.consistency_issues) == 0


class OWLReasoner:
    """Lightweight OWL reasoner for ontobuilder ontologies."""

    def __init__(self, ontology: Ontology) -> None:
        self.onto = ontology
        self._parent_map: dict[str, str | None] = {}
        self._children_map: dict[str, list[str]] = {}
        self._build_hierarchy()

    def _build_hierarchy(self) -> None:
        """Build parent/children lookup maps."""
        self._parent_map = {
            name: c.parent for name, c in self.onto.concepts.items()
        }
        self._children_map = {}
        for name in self.onto.concepts:
            self._children_map[name] = []
        for name, parent in self._parent_map.items():
            if parent and parent in self._children_map:
                self._children_map[parent].append(name)

    # -- Subclass inference --

    def get_ancestors(self, concept_name: str) -> list[str]:
        """Get all ancestor classes (transitive superclasses)."""
        ancestors = []
        current = self._parent_map.get(concept_name)
        while current:
            ancestors.append(current)
            current = self._parent_map.get(current)
        return ancestors

    def get_descendants(self, concept_name: str) -> list[str]:
        """Get all descendant classes (transitive subclasses)."""
        descendants = []
        stack = list(self._children_map.get(concept_name, []))
        while stack:
            child = stack.pop()
            descendants.append(child)
            stack.extend(self._children_map.get(child, []))
        return descendants

    def is_subclass_of(self, child: str, parent: str) -> bool:
        """Check if child is a (transitive) subclass of parent."""
        return parent in self.get_ancestors(child)

    # -- Property inheritance --

    def get_all_properties(self, concept_name: str) -> dict[str, dict]:
        """Get all properties for a concept, including inherited ones.

        Returns:
            Dict mapping property name to ``{"data_type": ..., "required": ...,
            "defined_on": ..., "inherited": ...}``.
        """
        props = {}
        # Walk ancestors from root → concept so closer definitions override
        chain = self.get_ancestors(concept_name)
        chain.reverse()
        chain.append(concept_name)

        for cls_name in chain:
            concept = self.onto.concepts.get(cls_name)
            if concept:
                for p in concept.properties:
                    props[p.name] = {
                        "data_type": p.data_type,
                        "required": p.required,
                        "defined_on": cls_name,
                        "inherited": cls_name != concept_name,
                    }
        return props

    # -- Instance classification --

    def classify_instance(self, instance_name: str) -> list[str]:
        """Get all classes an instance belongs to (direct + inferred ancestors)."""
        inst = self.onto.instances.get(instance_name)
        if not inst:
            return []
        types = [inst.concept]
        types.extend(self.get_ancestors(inst.concept))
        return types

    def find_instances_of(self, concept_name: str, include_subclasses: bool = True) -> list[str]:
        """Find all instances of a concept (optionally including subclass instances)."""
        target_classes = {concept_name}
        if include_subclasses:
            target_classes.update(self.get_descendants(concept_name))

        return [
            name for name, inst in self.onto.instances.items()
            if inst.concept in target_classes
        ]

    # -- Consistency checking --

    def check_consistency(self) -> list[str]:
        """Run consistency checks on the ontology.

        Checks for:
        - Circular inheritance
        - Orphaned parents (parent reference to non-existent concept)
        - Duplicate property names within inheritance chain
        - Instances of non-existent concepts
        - Relation endpoints referencing non-existent concepts
        - Instance property type mismatches
        """
        issues = []

        # Check circular inheritance
        for name in self.onto.concepts:
            visited = set()
            current = name
            while current:
                if current in visited:
                    issues.append(
                        f"Circular inheritance detected: {name} → ... → {current}"
                    )
                    break
                visited.add(current)
                current = self._parent_map.get(current)

        # Check orphaned parents
        for name, concept in self.onto.concepts.items():
            if concept.parent and concept.parent not in self.onto.concepts:
                issues.append(
                    f"Concept '{name}' references non-existent parent '{concept.parent}'"
                )

        # Check property type conflicts in inheritance chain
        for name in self.onto.concepts:
            seen: dict[str, str] = {}
            chain = self.get_ancestors(name)
            chain.reverse()
            chain.append(name)
            for cls_name in chain:
                concept = self.onto.concepts.get(cls_name)
                if concept:
                    for p in concept.properties:
                        if p.name in seen and seen[p.name] != p.data_type:
                            issues.append(
                                f"Property '{p.name}' type conflict: "
                                f"'{seen[p.name]}' on '{cls_name}' ancestor vs "
                                f"'{p.data_type}' on '{cls_name}'"
                            )
                        seen[p.name] = p.data_type

        # Check instances reference valid concepts
        for name, inst in self.onto.instances.items():
            if inst.concept not in self.onto.concepts:
                issues.append(
                    f"Instance '{name}' references non-existent concept '{inst.concept}'"
                )

        # Check relations reference valid concepts
        for name, rel in self.onto.relations.items():
            if rel.source not in self.onto.concepts:
                issues.append(
                    f"Relation '{name}' source '{rel.source}' does not exist"
                )
            if rel.target not in self.onto.concepts:
                issues.append(
                    f"Relation '{name}' target '{rel.target}' does not exist"
                )

        # Check instance property values match expected types
        type_checkers = {
            "string": lambda v: isinstance(v, str),
            "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "bool": lambda v: isinstance(v, bool),
        }
        for inst_name, inst in self.onto.instances.items():
            all_props = self.get_all_properties(inst.concept) if inst.concept in self.onto.concepts else {}
            for prop_name, value in inst.properties.items():
                if prop_name in all_props:
                    expected = all_props[prop_name]["data_type"]
                    checker = type_checkers.get(expected)
                    if checker and not checker(value):
                        issues.append(
                            f"Instance '{inst_name}' property '{prop_name}': "
                            f"expected {expected}, got {type(value).__name__}"
                        )

            # Check required properties are present
            for prop_name, info in all_props.items():
                if info["required"] and prop_name not in inst.properties:
                    issues.append(
                        f"Instance '{inst_name}' missing required property '{prop_name}'"
                    )

        return issues

    # -- Full inference --

    def run_inference(self) -> InferenceResult:
        """Run full inference and return all results."""
        result = InferenceResult()

        # Subclass inference
        for name in self.onto.concepts:
            ancestors = self.get_ancestors(name)
            if ancestors:
                result.inferred_subclasses[name] = ancestors

        # Property inheritance
        for name in self.onto.concepts:
            all_props = self.get_all_properties(name)
            inherited = [
                f"{p} ({info['data_type']}, from {info['defined_on']})"
                for p, info in all_props.items()
                if info["inherited"]
            ]
            if inherited:
                result.inherited_properties[name] = inherited

        # Instance classification
        for name in self.onto.instances:
            types = self.classify_instance(name)
            if len(types) > 1:
                result.instance_types[name] = types

        # Consistency
        result.consistency_issues = self.check_consistency()

        # Summary
        lines = [f"Inference results for '{self.onto.name}':"]
        lines.append(f"  Classes: {len(self.onto.concepts)}")
        lines.append(f"  Relations: {len(self.onto.relations)}")
        lines.append(f"  Instances: {len(self.onto.instances)}")
        lines.append(f"  Inferred subclass chains: {len(result.inferred_subclasses)}")
        lines.append(f"  Concepts with inherited properties: {len(result.inherited_properties)}")
        lines.append(f"  Instances with inferred types: {len(result.instance_types)}")
        if result.is_consistent:
            lines.append("  Consistency: OK")
        else:
            lines.append(f"  Consistency issues: {len(result.consistency_issues)}")
            for issue in result.consistency_issues:
                lines.append(f"    - {issue}")
        result.summary = "\n".join(lines)

        return result
