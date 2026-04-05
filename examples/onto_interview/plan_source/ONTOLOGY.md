# ONTOLOGY.md
> Agent instructions for designing, authoring, and connecting OWL ontologies to LLM pipelines.
> Place this file in your project root alongside `CLAUDE.md` or `AGENTS.md`.

---

## What this file is

This file instructs an LLM agent how to plan, write, and wire an OWL ontology for a given domain. Follow every section in order for a new ontology. For edits to an existing ontology, jump to the relevant section.

The agent should treat the `.ttl` file as the single source of truth. Everything else — prompt summaries, embeddings, validation rules — is derived from it.

---

## 0. Before you start — read the domain description

When the user describes their domain, extract:

1. **Nouns** → candidate Classes
2. **Verbs between nouns** → candidate ObjectProperties
3. **Numeric/string facts** → candidate DatatypeProperties
4. **Constraints** ("must have exactly one", "cannot be both") → Axioms
5. **Hierarchies** ("a Softgel is a ProductForm") → subClassOf relationships

Do not write any Turtle until you have listed all four categories and confirmed them with the user.

---

## 1. Naming conventions

| Element | Convention | Example |
|---|---|---|
| Namespace prefix | Short, domain-specific | `supp:`, `med:`, `fin:` |
| Namespace URI | Stable, versioned URI | `https://yourdomain.io/ontology#` |
| Class names | PascalCase, singular noun | `ContractManufacturer`, `RFP` |
| ObjectProperty names | camelCase, verb-first | `hasCapability`, `holdsCertification` |
| DatatypeProperty names | camelCase, verb-first | `hasMOQ`, `hasScore` |
| Individual names | PascalCase, proper noun | `NutraBioLabs`, `GMP` |
| File name | lowercase with underscores | `supplement.ttl` |

**Never use spaces, hyphens, or special characters in any OWL identifier.**

---

## 2. File structure — every `.ttl` file must follow this layout

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
# (controlled vocabularies — ProductForm, Certification, Status, etc.)

# ── Enumeration individuals ───────────────────────────────────────────
# (instances of the above)

# ── Object properties ─────────────────────────────────────────────────
# (links between classes)

# ── Datatype properties ───────────────────────────────────────────────
# (links to literal values)

# ── Axioms ────────────────────────────────────────────────────────────
# (cardinality, disjoint, restriction rules)

# ── Data individuals ──────────────────────────────────────────────────
# (real instances, if any — usually empty in schema-only ontologies)
```

Always include all eight sections, even if some are empty (leave a comment).

---

## 3. Class authoring rules

### 3a. Every class must have

```turtle
{prefix}:ClassName
    a owl:Class ;
    rdfs:label "Human readable name" ;
    rdfs:comment "One sentence: what is this class, when is something an instance of it." .
```

### 3b. Subclass hierarchy

```turtle
{prefix}:Child
    a owl:Class ;
    rdfs:subClassOf {prefix}:Parent .
```

- Maximum 3 levels of nesting for MVP ontologies.
- If you find yourself at level 4, flatten — likely a property is masquerading as a class.

### 3c. Disjoint classes

Declare disjoint when two classes **cannot share instances**:

```turtle
{prefix}:ClassA
    owl:disjointWith {prefix}:ClassB .
```

Default rule: if two classes are siblings (same parent), assume disjoint unless you have a reason they can overlap.

### 3d. Enumeration classes

Use for controlled vocabularies (statuses, types, categories):

```turtle
{prefix}:ProductForm a owl:Class ;
    rdfs:comment "The physical form of a supplement product." .

# Always declare all known individuals immediately after the class
{prefix}:Capsule  a {prefix}:ProductForm .
{prefix}:Softgel  a {prefix}:ProductForm .
{prefix}:Powder   a {prefix}:ProductForm .
{prefix}:Tablet   a {prefix}:ProductForm .
```

---

## 4. Property authoring rules

### 4a. ObjectProperty — links two individuals

```turtle
{prefix}:propertyName
    a owl:ObjectProperty ;
    rdfs:label "human readable label" ;
    rdfs:comment "What does this relationship mean? When does it hold?" ;
    rdfs:domain {prefix}:SubjectClass ;   # who has this property
    rdfs:range  {prefix}:ObjectClass .    # what it points to
```

### 4b. DatatypeProperty — links an individual to a literal

```turtle
{prefix}:propertyName
    a owl:DatatypeProperty ;
    rdfs:label "human readable label" ;
    rdfs:domain {prefix}:SubjectClass ;
    rdfs:range  xsd:integer .             # xsd:string | xsd:float | xsd:boolean | xsd:date
```

### 4c. Special property types — use when applicable

| Type | Turtle | Meaning |
|---|---|---|
| Functional | `a owl:FunctionalProperty` | At most one value per subject |
| Inverse functional | `a owl:InverseFunctionalProperty` | At most one subject per value |
| Transitive | `a owl:TransitiveProperty` | A→B and B→C implies A→C |
| Symmetric | `a owl:SymmetricProperty` | A→B implies B→A |
| Inverse of | `owl:inverseOf {prefix}:otherProp` | Bidirectional traversal |

### 4d. Property chains

Use when a two-hop relationship should be queryable as one:

```turtle
{prefix}:subjectToRegulation
    a owl:ObjectProperty ;
    owl:propertyChainAxiom (
        {prefix}:locatedIn
        {prefix}:hasRegulation
    ) .
```

---

## 5. Axiom authoring rules

### 5a. Cardinality restrictions

```turtle
# Exactly N
{prefix}:SomeClass rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty {prefix}:someProperty ;
    owl:cardinality 1
] .

# At least N
{prefix}:SomeClass rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty {prefix}:someProperty ;
    owl:minCardinality 1
] .

# At most N
{prefix}:SomeClass rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty {prefix}:someProperty ;
    owl:maxCardinality 3
] .
```

### 5b. Value restrictions

```turtle
# At least one value from range (existential)
{prefix}:SomeClass rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty {prefix}:someProperty ;
    owl:someValuesFrom {prefix}:RangeClass
] .

# All values from range (universal)
{prefix}:SomeClass rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty {prefix}:someProperty ;
    owl:allValuesFrom {prefix}:RangeClass
] .
```

### 5c. Boolean class expressions

```turtle
# Intersection (AND) — all conditions must hold
{prefix}:PremiumMatch owl:equivalentClass [
    owl:intersectionOf (
        {prefix}:Match
        {prefix}:HighScoreMatch
        {prefix}:CertificationCompleteMatch
    )
] .

# Union (OR) — any condition is sufficient
{prefix}:EligibleSupplier owl:equivalentClass [
    owl:unionOf (
        {prefix}:DomesticManufacturer
        {prefix}:FDARegisteredManufacturer
    )
] .
```

### 5d. Equivalent class — for external vocabulary mapping

```turtle
{prefix}:ContractManufacturer owl:equivalentClass [
    owl:intersectionOf (
        schema:Organization
        [ a owl:Restriction ;
          owl:onProperty {prefix}:holdsCertification ;
          owl:someValuesFrom {prefix}:GMPFamily ]
    )
] .
```

---

## 6. Self-check before saving the `.ttl` file

Run through every item. If any fails, fix before proceeding.

```
[ ] Every class has: a owl:Class, rdfs:label, rdfs:comment
[ ] Every property has: rdfs:domain, rdfs:range, rdfs:comment
[ ] Every enumeration class is followed by all known individuals
[ ] Sibling classes that cannot overlap have owl:disjointWith
[ ] Any property that should have exactly one value is owl:FunctionalProperty
[ ] Any class whose instance must have at least one of a property has owl:minCardinality 1
[ ] No class name is also used as a property name
[ ] No circular subClassOf chains exist
[ ] Namespace prefix is declared at the top
[ ] File parses without error (mentally validate prefix usage)
```

---

## 7. Generate the LLM prompt summary

After the `.ttl` file is validated, generate a structured English summary using this template. This is what gets injected into the system prompt.

### Template

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

## Matching / reasoning instructions
{domain-specific instructions for how to apply the ontology}
```

### Rules section translation guide

| OWL Axiom | Plain English |
|---|---|
| `owl:cardinality 1` | "{Class} must have exactly one {property}. Never zero, never two." |
| `owl:minCardinality 1` | "{Class} must have at least one {property}. Zero is invalid." |
| `owl:FunctionalProperty` | "{property} has at most one value per {domain class}." |
| `owl:disjointWith` | "No entity can be both {ClassA} and {ClassB} simultaneously." |
| `owl:someValuesFrom` | "At least one {property} value must be of type {range}." |
| `owl:allValuesFrom` | "Every {property} value must be of type {range} — no exceptions." |
| `owl:TransitiveProperty` | "If A {property} B and B {property} C, then A {property} C is also true." |
| `owl:propertyChainAxiom` | "If X {prop1} Y and Y {prop2} Z, then X {inferredProp} Z is implied." |
| `owl:inverseOf` | "{propA} and {propB} are inverse: if A {propA} B, then B {propB} A." |

---

## 8. Injection strategies — choose based on ontology size

### Strategy 1: Full injection (< 50 classes)

Paste the entire English summary into the system prompt. Regenerate whenever the ontology changes.

```python
ONTOLOGY_CONTEXT = ontology_to_english("ontology/domain.ttl")

system_prompt = f"""
{ONTOLOGY_CONTEXT}

{task_specific_instructions}
"""
```

### Strategy 2: Summary injection (50–200 classes)

Generate a compressed summary (class names + key properties only, no full comments). Inject the summary; keep full detail in a reference file.

```python
ONTOLOGY_SUMMARY = ontology_to_summary("ontology/domain.ttl", max_tokens=800)
```

### Strategy 3: Ontology RAG (200+ classes)

Embed each class definition as a separate vector. At query time, retrieve the top-k relevant class definitions and inject only those.

```python
# At startup
embed_ontology("ontology/domain.ttl", pgvector_conn)

# At query time
relevant = retrieve_relevant_classes(user_query, pgvector_conn, k=5)
system_prompt = BASE_INSTRUCTIONS + "\n\n## Relevant ontology context\n" + relevant
```

---

## 9. Output schema instructions

When the LLM must produce structured output that maps to ontology individuals, add this section to the system prompt:

```
## Output format

Your output must be valid JSON matching this schema:

{
  "@type": "{prefix}:{ClassName}",
  "{prefix}:{property1}": "{value}",
  "{prefix}:{property2}": number,
  ...
}

Rules:
- "@type" must be a valid class from this ontology
- All required properties (minCardinality ≥ 1) must be present
- Functional properties must have exactly one value (string, not array)
- Multi-valued properties must be arrays even if only one value
- Enumeration values must match exactly: {list of valid values}
```

---

## 10. Validation rules — check every LLM output

After receiving an LLM output, validate against these rules before saving:

### Required checks (hard failures — reject output)

```python
def validate_ontology_output(output: dict, ontology_rules: dict) -> list[str]:
    errors = []

    # 1. Required properties present (minCardinality rules)
    for prop in ontology_rules["required_properties"]:
        if prop not in output:
            errors.append(f"Missing required property: {prop}")

    # 2. Functional properties have single values (not lists)
    for prop in ontology_rules["functional_properties"]:
        if prop in output and isinstance(output[prop], list):
            errors.append(f"Functional property {prop} must be a single value, not a list")

    # 3. Enumeration values are valid
    for prop, valid_values in ontology_rules["enum_properties"].items():
        val = output.get(prop)
        if val and val not in valid_values:
            errors.append(f"{prop} value '{val}' not in {valid_values}")

    # 4. Score ranges
    for prop, (min_val, max_val) in ontology_rules["range_properties"].items():
        val = output.get(prop)
        if val is not None and not (min_val <= val <= max_val):
            errors.append(f"{prop} = {val} out of range [{min_val}, {max_val}]")

    return errors
```

### On validation failure — re-prompt pattern

```python
async def generate_with_validation(prompt, ontology_rules, max_retries=2):
    for attempt in range(max_retries + 1):
        output = await call_llm(prompt)
        errors = validate_ontology_output(output, ontology_rules)

        if not errors:
            return output

        if attempt < max_retries:
            # Inject errors into next prompt
            error_context = "\n".join(f"- {e}" for e in errors)
            prompt = prompt + f"""

Your previous output had ontology violations:
{error_context}

Please regenerate, fixing each violation above.
"""

    raise ValueError(f"Output failed validation after {max_retries} retries: {errors}")
```

---

## 11. Ontology evolution — how to update safely

When the domain changes, follow this sequence. **Never skip steps.**

```
1. Edit the .ttl file (classes, properties, or axioms)
2. Run the self-check from Section 6
3. Regenerate the English summary (Section 7)
4. Update the system prompt with the new summary
5. Re-run validation on any cached LLM outputs that touch changed classes
6. Bump owl:versionInfo in the ontology declaration
7. Commit both the .ttl file and the generated summary together
```

### Safe changes (backward compatible)

- Adding a new class
- Adding a new property
- Adding new enumeration individuals
- Loosening a cardinality restriction (1 → minCardinality 1)

### Breaking changes (require migration)

- Renaming a class or property
- Tightening a cardinality restriction
- Adding `owl:disjointWith` to existing classes
- Removing a class or property

For breaking changes, add a comment block at the top of the `.ttl` file:

```turtle
# BREAKING CHANGE v0.2.0 → v0.3.0:
# - Renamed hasManufacturerCapability → hasCapability
# - Added disjointWith between ContractManufacturer and SupplementBrand
# Migration: update all system prompts, re-validate all Match records
```

---

## 12. Common mistakes — do not do these

| Mistake | Why it's wrong | Correct approach |
|---|---|---|
| Making every concept a class | Inflates ontology, harder to query | Only promote to class if it has its own attributes or relationships |
| Using string literals for enumeration values | LLM can hallucinate spellings | Define an enumeration class with explicit individuals |
| Skipping `rdfs:comment` | LLM cannot generate accurate summaries | Every class and property needs a comment |
| Putting all logic in the system prompt instead of the ontology | Prompt drift, inconsistency | Logic belongs in axioms; prompt references the axioms |
| Injecting raw Turtle into the system prompt | LLM reads it literally, misses semantic meaning | Always convert to English summary first |
| One massive prompt with entire ontology | Token bloat, diluted attention | Use RAG strategy when > 50 classes |
| Never validating LLM output | Silent schema violations corrupt data | Always run Section 10 checks before saving |
| Hardcoding enumeration values in application code | Drift from ontology | Read valid values from the .ttl file at startup |

---

## 13. Quick reference — OWL axiom → English prompt mapping

Copy the relevant rows into your system prompt's Rules section.

```
owl:FunctionalProperty on P          →  "{Domain} has exactly one {P}. Never include multiple values."
owl:cardinality 1 on P               →  "{Class} must reference exactly one {P}. Zero or two+ is invalid."
owl:minCardinality 1 on P            →  "{Class} must have at least one {P}. An instance without it is malformed."
owl:disjointWith B                   →  "No entity is both {A} and {B}. If a record appears to be both, flag it."
owl:someValuesFrom C on P            →  "At least one {P} value must be a {C}. Other types are allowed alongside."
owl:allValuesFrom C on P             →  "Every {P} value must be a {C}. Any exception is a violation."
owl:TransitiveProperty               →  "{P} is transitive: A→B and B→C implies A→C. Apply this when traversing hierarchies."
owl:inverseOf Q                      →  "{P} and {Q} are inverses: if A {P} B, then B {Q} A is also true."
owl:propertyChainAxiom (P1 P2)       →  "If X {P1} Y and Y {P2} Z, then X {inferredProp} Z — traverse this chain."
owl:equivalentClass [intersectionOf] →  "{A} is {B} AND {C}: both conditions must hold for something to be an {A}."
owl:equivalentClass [unionOf]        →  "{A} is {B} OR {C}: either condition is sufficient."
```

---

## 14. File checklist — what belongs in your project

```
project/
├── ONTOLOGY.md              ← this file (agent instructions)
├── CLAUDE.md                ← general agent instructions
├── ontology/
│   ├── domain.ttl           ← source of truth (hand-authored)
│   ├── domain_summary.txt   ← generated English summary (auto-generated, committed)
│   └── CHANGELOG.md         ← ontology version history
├── scripts/
│   ├── ontology_to_prompt.py   ← generates domain_summary.txt from domain.ttl
│   ├── embed_ontology.py       ← loads embeddings into pgvector (RAG strategy)
│   └── validate_output.py      ← validates LLM outputs against ontology rules
└── tests/
    └── test_ontology.py     ← unit tests: parse, validate, round-trip
```

---

## 15. Minimal working example — copy this to bootstrap

Substitute `{prefix}`, `{domain}`, and `{ClassName}` with your domain's values.

### `ontology/domain.ttl`

```turtle
@prefix {prefix}: <https://yourdomain.io/ontology#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

<https://yourdomain.io/ontology#>
    a owl:Ontology ;
    rdfs:label "{Domain} Ontology" ;
    owl:versionInfo "0.1.0" .

# ── Core classes ──────────────────────────────────────────────────────
{prefix}:EntityA
    a owl:Class ;
    rdfs:label "Entity A" ;
    rdfs:comment "Describe what EntityA is and when something qualifies as one." ;
    owl:disjointWith {prefix}:EntityB .

{prefix}:EntityB
    a owl:Class ;
    rdfs:label "Entity B" ;
    rdfs:comment "Describe what EntityB is and when something qualifies as one." .

{prefix}:RelationshipNode
    a owl:Class ;
    rdfs:label "Relationship Node" ;
    rdfs:comment "Links EntityA to EntityB with a score and explanation." .

# ── Enumeration classes ───────────────────────────────────────────────
{prefix}:Category
    a owl:Class ;
    rdfs:comment "Controlled vocabulary for categories." .

{prefix}:CategoryA  a {prefix}:Category .
{prefix}:CategoryB  a {prefix}:Category .

# ── Object properties ─────────────────────────────────────────────────
{prefix}:hasCategory
    a owl:ObjectProperty ;
    rdfs:comment "Links EntityA to one or more categories it belongs to." ;
    rdfs:domain {prefix}:EntityA ;
    rdfs:range  {prefix}:Category .

{prefix}:linksTo
    a owl:ObjectProperty , owl:FunctionalProperty ;
    rdfs:comment "Each RelationshipNode links to exactly one EntityA." ;
    rdfs:domain {prefix}:RelationshipNode ;
    rdfs:range  {prefix}:EntityA .

# ── Datatype properties ───────────────────────────────────────────────
{prefix}:hasScore
    a owl:DatatypeProperty ;
    rdfs:comment "Confidence score for a RelationshipNode. Range: 0.0–1.0." ;
    rdfs:domain {prefix}:RelationshipNode ;
    rdfs:range  xsd:float .

# ── Axioms ────────────────────────────────────────────────────────────
{prefix}:RelationshipNode rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty {prefix}:linksTo ;
    owl:cardinality 1
] .
```

### `scripts/ontology_to_prompt.py`

```python
from rdflib import Graph, RDF, RDFS, OWL, Namespace
from pathlib import Path

def ontology_to_english(ttl_path: str) -> str:
    g = Graph()
    g.parse(ttl_path, format="turtle")
    lines = []

    # Detect namespace
    for prefix, ns in g.namespaces():
        if prefix not in ("owl", "rdf", "rdfs", "xsd", ""):
            domain_ns = Namespace(ns)
            break

    lines.append("## Classes")
    for cls in sorted(g.subjects(RDF.type, OWL.Class)):
        name = str(cls).split("#")[-1]
        if not name:
            continue
        comment = g.value(cls, RDFS.comment)
        parent  = g.value(cls, RDFS.subClassOf)
        line = f"- **{name}**"
        if parent and "#" in str(parent):
            line += f" (subclass of {str(parent).split('#')[-1]})"
        if comment:
            line += f": {comment}"
        lines.append(line)

    lines.append("\n## Properties")
    for prop in sorted(g.subjects(RDF.type, OWL.ObjectProperty)):
        name    = str(prop).split("#")[-1]
        domain  = g.value(prop, RDFS.domain)
        range_  = g.value(prop, RDFS.range)
        comment = g.value(prop, RDFS.comment)
        d = str(domain).split("#")[-1] if domain else "?"
        r = str(range_).split("#")[-1] if range_  else "?"
        line = f"- **{name}** ({d} → {r})"
        if comment:
            line += f": {comment}"
        lines.append(line)

    for prop in sorted(g.subjects(RDF.type, OWL.DatatypeProperty)):
        name    = str(prop).split("#")[-1]
        domain  = g.value(prop, RDFS.domain)
        range_  = g.value(prop, RDFS.range)
        comment = g.value(prop, RDFS.comment)
        d = str(domain).split("#")[-1] if domain else "?"
        r = str(range_).split("#")[-1] if range_  else "?"
        line = f"- **{name}** ({d} → {r})"
        if comment:
            line += f": {comment}"
        lines.append(line)

    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    ttl = sys.argv[1] if len(sys.argv) > 1 else "ontology/domain.ttl"
    summary = ontology_to_english(ttl)
    out = Path(ttl).with_suffix("").name + "_summary.txt"
    Path(f"ontology/{out}").write_text(summary)
    print(f"Written to ontology/{out}")
    print(summary)
```

---

*End of ONTOLOGY.md*
