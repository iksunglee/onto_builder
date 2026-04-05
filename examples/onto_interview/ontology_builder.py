"""Parse LLM-generated Turtle and summary text, and bridge to ontobuilder core model."""

from __future__ import annotations

import re
import yaml
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ontobuilder.core.ontology import Ontology


def extract_code_block(text: str, lang: str = "turtle") -> str | None:
    """Extract the first code block of the given language from LLM response text."""
    pattern = rf"```{lang}\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def extract_turtle_block(text: str) -> str | None:
    """Extract Turtle (.ttl) code block from LLM response."""
    return extract_code_block(text, "turtle")


def extract_text_block(text: str) -> str | None:
    """Extract a plain text code block from LLM response."""
    return extract_code_block(text, "text")


def extract_yaml_block(text: str) -> str | None:
    """Extract YAML code block from LLM response."""
    result = extract_code_block(text, "yaml")
    if result is None:
        result = extract_code_block(text, "yml")
    return result


def parse_turtle_to_ontology(turtle_text: str) -> Ontology:
    """Parse Turtle text into an ontobuilder Ontology (best-effort, for display).

    This extracts classes, properties, and relations from the Turtle text
    using regex patterns. For full OWL reasoning, use rdflib.
    """
    # Extract ontology name from rdfs:label on the Ontology declaration
    name_match = re.search(r'a\s+owl:Ontology\s*;[^.]*rdfs:label\s+"([^"]+)"', turtle_text, re.DOTALL)
    name = name_match.group(1) if name_match else "Untitled Ontology"

    # Detect prefix
    prefix_match = re.search(r'@prefix\s+(\w+):\s*<([^>]+)>', turtle_text)
    prefix = prefix_match.group(1) if prefix_match else "ns"

    onto = Ontology(name=name.replace(" Ontology", ""))

    # Extract classes: {prefix}:ClassName a owl:Class
    class_pattern = rf'{prefix}:(\w+)\s+a\s+owl:Class'
    classes = re.findall(class_pattern, turtle_text)

    # Extract rdfs:comment for each class
    class_comments = {}
    for cls in classes:
        comment_match = re.search(
            rf'{prefix}:{cls}\s[^.]*rdfs:comment\s+"([^"]+)"',
            turtle_text, re.DOTALL
        )
        if comment_match:
            class_comments[cls] = comment_match.group(1)

    # Extract subClassOf relationships
    subclass_map = {}
    subclass_pattern = rf'{prefix}:(\w+)\s[^.]*rdfs:subClassOf\s+{prefix}:(\w+)'
    for child, parent in re.findall(subclass_pattern, turtle_text):
        if child in classes and parent in classes:
            subclass_map[child] = parent

    # Add classes in parent-first order
    added = set()
    remaining = list(classes)
    max_passes = len(remaining) + 1
    while remaining and max_passes > 0:
        max_passes -= 1
        still_remaining = []
        for cls in remaining:
            parent = subclass_map.get(cls)
            if parent and parent not in added:
                still_remaining.append(cls)
            else:
                onto.add_concept(
                    cls,
                    description=class_comments.get(cls, ""),
                    parent=parent if parent in added else None,
                )
                added.add(cls)
        remaining = still_remaining

    # Extract DatatypeProperties → ontobuilder properties
    dt_prop_pattern = rf'{prefix}:(\w+)\s+a\s+owl:DatatypeProperty'
    dt_props = re.findall(dt_prop_pattern, turtle_text)
    for prop in dt_props:
        domain_match = re.search(rf'{prefix}:{prop}\s[^.]*rdfs:domain\s+{prefix}:(\w+)', turtle_text, re.DOTALL)
        range_match = re.search(rf'{prefix}:{prop}\s[^.]*rdfs:range\s+xsd:(\w+)', turtle_text, re.DOTALL)
        if domain_match and domain_match.group(1) in added:
            xsd_type = range_match.group(1) if range_match else "string"
            # Map xsd types to ontobuilder types
            type_map = {
                "string": "string", "integer": "int", "int": "int",
                "float": "float", "double": "float",
                "boolean": "bool", "date": "date", "dateTime": "date",
            }
            dt = type_map.get(xsd_type, "string")
            # Check if functional
            is_functional = bool(re.search(
                rf'{prefix}:{prop}\s+a\s+[^.]*owl:FunctionalProperty',
                turtle_text, re.DOTALL
            ))
            try:
                onto.add_property(
                    domain_match.group(1), prop, data_type=dt, required=is_functional
                )
            except Exception:
                pass

    # Extract ObjectProperties → ontobuilder relations
    obj_prop_pattern = rf'{prefix}:(\w+)\s+a\s+owl:ObjectProperty'
    obj_props = re.findall(obj_prop_pattern, turtle_text)
    for prop in obj_props:
        domain_match = re.search(rf'{prefix}:{prop}\s[^.]*rdfs:domain\s+{prefix}:(\w+)', turtle_text, re.DOTALL)
        range_match = re.search(rf'{prefix}:{prop}\s[^.]*rdfs:range\s+{prefix}:(\w+)', turtle_text, re.DOTALL)
        if domain_match and range_match:
            source = domain_match.group(1)
            target = range_match.group(1)
            if source in added and target in added:
                try:
                    onto.add_relation(prop, source=source, target=target)
                except Exception:
                    pass

    return onto


def ontology_to_yaml(onto: Ontology) -> str:
    """Serialize an Ontology to YAML string."""
    return yaml.dump(onto.to_dict(), default_flow_style=False, sort_keys=False)
