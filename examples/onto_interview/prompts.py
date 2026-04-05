"""Prompt templates for the OWL ontology interview tool.

Based on the methodology in plan_source/ONTOLOGY.md:
- Extract nouns → Classes
- Extract verbs between nouns → ObjectProperties
- Extract numeric/string facts → DatatypeProperties
- Extract constraints → Axioms
- Extract hierarchies → subClassOf
"""

SYSTEM_PROMPT = """\
You are an expert ontology engineer conducting an interview to build an OWL domain ontology.

Your methodology (follow strictly):
1. Understand the domain through conversation
2. Extract from the user's descriptions:
   - Nouns → candidate Classes
   - Verbs between nouns → candidate ObjectProperties
   - Numeric/string facts → candidate DatatypeProperties
   - Constraints ("must have exactly one", "cannot be both") → Axioms
   - Hierarchies ("a Dog is an Animal") → subClassOf relationships
3. Confirm the extracted elements with the user before generating

Naming conventions:
- Namespace prefix: short, domain-specific (e.g., supp:, med:, fin:)
- Class names: PascalCase, singular noun (e.g., ContractManufacturer, Product)
- ObjectProperty names: camelCase, verb-first (e.g., hasCapability, belongsTo)
- DatatypeProperty names: camelCase, verb-first (e.g., hasPrice, hasName)
- Individual names: PascalCase, proper noun (e.g., GMP, Capsule)

OWL constructs to consider:
- subClassOf for hierarchies (max 3 levels for MVP)
- owl:disjointWith for sibling classes that cannot share instances
- owl:FunctionalProperty for single-value properties
- owl:cardinality for exact count constraints
- owl:someValuesFrom / owl:allValuesFrom for value restrictions
- Enumeration classes for controlled vocabularies (statuses, types, categories)
- owl:TransitiveProperty for transitive chains (e.g., isPartOf)
- owl:propertyChainAxiom for inferred multi-hop relationships
- owl:equivalentClass for external vocabulary mapping

Guidelines:
- Be friendly, clear, and educational. The user may be new to ontologies.
- Ask focused questions, one at a time. Don't overwhelm.
- After gathering enough context (usually 4-8 exchanges), offer to generate.
- When you identify concepts, explain WHY they matter.
- Keep responses concise — 2-4 sentences for questions.
"""

INTERVIEW_OPENER = """\
Start the interview by greeting the user and asking what domain they want to build \
an ontology for. Be warm and brief. Ask ONE question only."""

EXTRACTION_PROMPT = """\
Based on the interview conversation so far, extract the following elements from the \
user's domain description. Return them in a structured format:

## Extracted Elements

### Classes (from nouns)
List each candidate class with:
- Name (PascalCase)
- Description (one sentence)
- Parent class (if any)
- Whether it's an enumeration class (controlled vocabulary)

### ObjectProperties (from verbs between nouns)
List each relationship with:
- Name (camelCase, verb-first)
- Domain (source class)
- Range (target class)
- Special type (Functional, Transitive, Symmetric, or none)
- Inverse property name (if applicable)

### DatatypeProperties (from facts)
List each data attribute with:
- Name (camelCase, verb-first)
- Domain (which class)
- Range (xsd:string, xsd:integer, xsd:float, xsd:boolean, xsd:date)
- Whether it's Functional (single value)

### Enumeration Individuals
For each enumeration class, list its known values.

### Axioms (from constraints)
List each constraint with:
- Type (disjoint, cardinality, someValuesFrom, allValuesFrom, propertyChain, equivalentClass)
- Description in plain English
- The classes/properties involved

### Hierarchies
List parent → child relationships.

Ask the user to confirm or modify these extractions before proceeding to generation."""

GENERATE_TURTLE_PROMPT = """\
Based on the confirmed domain elements from the interview, generate a complete OWL \
ontology in Turtle (.ttl) format.

Follow this EXACT file structure:

```turtle
# ── Prefixes ─────────────────────────────────────────────────────────
@prefix {prefix}: <{namespace_uri}> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

# ── Ontology declaration ──────────────────────────────────────────────
<{namespace_uri}>
    a owl:Ontology ;
    rdfs:label "{Domain Name} Ontology" ;
    owl:versionInfo "0.1.0" .

# ── Abstract superclasses ─────────────────────────────────────────────
# (shared parents — define before subclasses)

# ── Core classes ──────────────────────────────────────────────────────
# (main domain entities)

# ── Enumeration classes ───────────────────────────────────────────────
# (controlled vocabularies)

# ── Enumeration individuals ───────────────────────────────────────────
# (instances of enumeration classes)

# ── Object properties ─────────────────────────────────────────────────
# (links between classes)

# ── Datatype properties ───────────────────────────────────────────────
# (links to literal values)

# ── Axioms ────────────────────────────────────────────────────────────
# (cardinality, disjoint, restriction rules)

# ── Data individuals ──────────────────────────────────────────────────
# (real instances, if any)
```

Rules:
- Every class MUST have: a owl:Class, rdfs:label, rdfs:comment
- Every property MUST have: rdfs:domain, rdfs:range, rdfs:comment
- Every enumeration class must be followed by all known individuals
- Sibling classes that cannot overlap must have owl:disjointWith
- Single-value properties should be owl:FunctionalProperty
- No spaces, hyphens, or special characters in OWL identifiers
- Maximum 3 levels of nesting for hierarchies
- Include ALL eight sections even if some are empty (leave a comment)

After the Turtle code block, provide a brief explanation of key design decisions.

IMPORTANT: The Turtle must be valid and parseable. Use correct Turtle syntax."""

GENERATE_SUMMARY_PROMPT = """\
Based on the Turtle ontology just generated, create an English summary suitable for \
injection into an LLM system prompt. Follow this template:

```
You reason over a {domain} ontology.

## Classes
{for each class:}
- **{ClassName}**: {rdfs:comment}. {if subclass: "Subclass of {Parent}."}

## Properties
{for each ObjectProperty:}
- **{propertyName}** ({domain} → {range}): {rdfs:comment}

{for each DatatypeProperty:}
- **{propertyName}** ({domain} → {xsd type}): {rdfs:comment}

## Enumeration values
{for each enumeration class:}
- **{ClassName}** instances: {comma-separated list of individual names}

## Rules
{for each axiom, in plain English:}
- {plain English statement of the rule}
```

Use this translation guide for axioms:
- owl:FunctionalProperty → "{Domain} has exactly one {P}. Never include multiple values."
- owl:cardinality 1 → "{Class} must reference exactly one {P}. Zero or two+ is invalid."
- owl:minCardinality 1 → "{Class} must have at least one {P}. An instance without it is malformed."
- owl:disjointWith → "No entity is both {A} and {B}. If a record appears to be both, flag it."
- owl:someValuesFrom → "At least one {P} value must be a {C}."
- owl:allValuesFrom → "Every {P} value must be a {C}. Any exception is a violation."
- owl:TransitiveProperty → "{P} is transitive: A→B and B→C implies A→C."
- owl:inverseOf → "{P} and {Q} are inverses."
- owl:propertyChainAxiom → "If X {P1} Y and Y {P2} Z, then X {inferred} Z."

Return the summary inside a ```text code block."""

VALIDATION_CHECKLIST = """\
Run through this self-check on the generated Turtle file. Report pass/fail for each:

1. [ ] Every class has: a owl:Class, rdfs:label, rdfs:comment
2. [ ] Every property has: rdfs:domain, rdfs:range, rdfs:comment
3. [ ] Every enumeration class is followed by all known individuals
4. [ ] Sibling classes that cannot overlap have owl:disjointWith
5. [ ] Any property that should have exactly one value is owl:FunctionalProperty
6. [ ] Any class whose instance must have at least one of a property has owl:minCardinality 1
7. [ ] No class name is also used as a property name
8. [ ] No circular subClassOf chains exist
9. [ ] Namespace prefix is declared at the top
10. [ ] File parses without error (validate prefix usage)

Return results as a checklist with [x] for pass and [ ] for fail, with brief notes on any failures."""

REFINE_TURTLE_PROMPT = """\
The user wants to modify the generated ontology. Apply their requested changes to the \
Turtle file and return the UPDATED complete ontology.

Current Turtle ontology:
```turtle
{current_turtle}
```

Rules:
- Keep everything the user didn't ask to change
- Maintain all eight sections in the file structure
- Ensure every new/modified element follows the authoring rules
- Update the English summary if structural changes were made

Return the updated Turtle inside a ```turtle code block.
After the code block, briefly explain what you changed."""
