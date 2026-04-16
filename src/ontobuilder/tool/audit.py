# src/ontobuilder/tool/audit.py
"""Ontology quality auditor — heuristic checks with scored report."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ontobuilder.core.ontology import Ontology


@dataclass
class AuditItem:
    """A single audit finding."""

    check: str
    severity: str  # CRITICAL, WARNING, SUGGESTION
    detail: str
    penalty: int = 0


@dataclass
class AuditResult:
    """Complete audit report."""

    score: int  # 0-100
    items: list[AuditItem] = field(default_factory=list)

    @property
    def summary(self) -> str:
        critical = sum(1 for i in self.items if i.severity == "CRITICAL")
        warning = sum(1 for i in self.items if i.severity == "WARNING")
        suggestion = sum(1 for i in self.items if i.severity == "SUGGESTION")
        return (
            f"Score: {self.score}/100 — "
            f"{critical} critical, {warning} warnings, {suggestion} suggestions"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "summary": self.summary,
            "items": [
                {
                    "check": i.check,
                    "severity": i.severity,
                    "detail": i.detail,
                    "penalty": i.penalty,
                }
                for i in self.items
            ],
        }


_PASCAL_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")


class OntologyAuditor:
    """Run heuristic quality checks on an ontology."""

    def audit(self, onto: Ontology) -> AuditResult:
        items: list[AuditItem] = []

        items.extend(self._check_no_concepts(onto))
        items.extend(self._check_missing_descriptions(onto))
        items.extend(self._check_orphan_concepts(onto))
        items.extend(self._check_sparse_properties(onto))
        items.extend(self._check_hierarchy_issues(onto))
        items.extend(self._check_naming_inconsistencies(onto))
        items.extend(self._check_instance_coverage(onto))
        items.extend(self._check_missing_required_id(onto))

        total_penalty = sum(i.penalty for i in items)
        score = max(0, 100 - total_penalty)
        return AuditResult(score=score, items=items)

    def _check_no_concepts(self, onto: Ontology) -> list[AuditItem]:
        if not onto.concepts:
            return [
                AuditItem(
                    check="no_concepts",
                    severity="CRITICAL",
                    detail="Ontology has no concepts defined",
                    penalty=55,
                )
            ]
        return []

    def _check_missing_descriptions(self, onto: Ontology) -> list[AuditItem]:
        items = []
        for name, concept in onto.concepts.items():
            if not concept.description:
                items.append(
                    AuditItem(
                        check="missing_descriptions",
                        severity="WARNING",
                        detail=f"Concept '{name}' has no description",
                        penalty=3,
                    )
                )
        return items

    def _check_orphan_concepts(self, onto: Ontology) -> list[AuditItem]:
        if len(onto.concepts) < 2:
            return []
        connected: set[str] = set()
        for rel in onto.relations.values():
            connected.add(rel.source)
            connected.add(rel.target)
        for concept in onto.concepts.values():
            if concept.parent:
                connected.add(concept.name)
                connected.add(concept.parent)

        orphans = [n for n in onto.concepts if n not in connected]
        items = []
        for name in orphans:
            items.append(
                AuditItem(
                    check="orphan_concepts",
                    severity="WARNING",
                    detail=f"Concept '{name}' has no relations or parent/child links",
                    penalty=5,
                )
            )
        return items

    def _check_sparse_properties(self, onto: Ontology) -> list[AuditItem]:
        items = []
        for name, concept in onto.concepts.items():
            if not concept.properties:
                items.append(
                    AuditItem(
                        check="sparse_properties",
                        severity="SUGGESTION",
                        detail=f"Concept '{name}' has no properties",
                        penalty=2,
                    )
                )
            elif len(concept.properties) == 1:
                items.append(
                    AuditItem(
                        check="sparse_properties",
                        severity="SUGGESTION",
                        detail=f"Concept '{name}' has only 1 property",
                        penalty=1,
                    )
                )
        return items

    def _check_hierarchy_issues(self, onto: Ontology) -> list[AuditItem]:
        if len(onto.concepts) < 4:
            return []
        has_parent = any(c.parent for c in onto.concepts.values())
        if not has_parent:
            return [
                AuditItem(
                    check="hierarchy_issues",
                    severity="WARNING",
                    detail=(
                        f"All {len(onto.concepts)} concepts are at root level — "
                        "consider adding a class hierarchy"
                    ),
                    penalty=5,
                )
            ]

        items = []
        for name in onto.concepts:
            depth = 0
            current = name
            visited: set[str] = set()
            while current and current in onto.concepts:
                if current in visited:
                    break
                visited.add(current)
                parent = onto.concepts[current].parent
                if parent:
                    depth += 1
                current = parent
            if depth > 5:
                items.append(
                    AuditItem(
                        check="hierarchy_issues",
                        severity="WARNING",
                        detail=f"Concept '{name}' is {depth} levels deep — consider flattening",
                        penalty=3,
                    )
                )
        return items

    def _check_naming_inconsistencies(self, onto: Ontology) -> list[AuditItem]:
        if len(onto.concepts) < 2:
            return []
        pascal_count = sum(1 for n in onto.concepts if _PASCAL_RE.match(n))
        other_count = len(onto.concepts) - pascal_count
        if pascal_count > 0 and other_count > 0:
            non_pascal = [n for n in onto.concepts if not _PASCAL_RE.match(n)]
            return [
                AuditItem(
                    check="naming_inconsistencies",
                    severity="WARNING",
                    detail=(
                        f"Mixed naming: {pascal_count} PascalCase, {other_count} other — "
                        f"non-PascalCase: {', '.join(non_pascal[:5])}"
                    ),
                    penalty=3,
                )
            ]
        return []

    def _check_instance_coverage(self, onto: Ontology) -> list[AuditItem]:
        if not onto.concepts:
            return []
        concepts_with_instances = {i.concept for i in onto.instances.values()}
        items = []
        for name in onto.concepts:
            if name not in concepts_with_instances:
                items.append(
                    AuditItem(
                        check="instance_coverage",
                        severity="SUGGESTION",
                        detail=f"Concept '{name}' has no instances",
                        penalty=1,
                    )
                )
        return items

    def _check_missing_required_id(self, onto: Ontology) -> list[AuditItem]:
        items = []
        for name, concept in onto.concepts.items():
            has_required = any(p.required for p in concept.properties)
            if concept.properties and not has_required:
                items.append(
                    AuditItem(
                        check="missing_required_id",
                        severity="SUGGESTION",
                        detail=(
                            f"Concept '{name}' has properties but none are required — "
                            "consider marking a primary identifier as required"
                        ),
                        penalty=1,
                    )
                )
        return items
