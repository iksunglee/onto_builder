# RAG-Friendly Export: System Prompt + JSON-LD + Schema Card

## TL;DR

> **Quick Summary**: Add three new export formats to ontobuilder so that ontologies can be consumed by LLMs for RAG — a human-readable system prompt text, a JSON-LD structured grounding format, and a Schema Card vocabulary summary. Must be beginner-friendly, editable, and require zero new dependencies.
>
> **Deliverables**:
> - System prompt text exporter (`prompt_io.py`) — compact readable text for LLM system messages
> - JSON-LD exporter (`jsonld_io.py`) — structured grounding with `@context`/`@id`/`@type`
> - Schema Card exporter (`schemacard_io.py`) — OntoRAG-compatible vocabulary summary
> - CLI integration — `onto export --format prompt|jsonld|schema-card`
> - Streamlit UI — RAG exports section with download buttons
> - Shared test fixtures (`conftest.py`) + full test coverage
>
> **Estimated Effort**: Medium (7 tasks, ~3 hours implementation)
> **Parallel Execution**: YES — 3 waves
> **Critical Path**: Task 1 → Tasks 2,3,4 (parallel) → Tasks 5,6 (parallel) → Task 7

---

## Context

### Original Request
User wants ontobuilder's ontologies to be "more friendly and compatible with LLM like OpenAI" — specifically for RAG (retrieval-augmented generation). Two confirmed use cases: (1) inject ontology as system prompt context so LLMs understand the domain schema, (2) export as JSON-LD for structured grounding.

### Interview Summary
**Key Discussions**:
- Compared ontobuilder to Palantir Foundry Ontology — similar semantic model (concepts/properties/relations) but different purpose (LLM-assisted building vs enterprise operational layer)
- Identified that current exports (YAML/JSON only) have zero LLM-consumable formats
- User confirmed: system prompt context + JSON-LD structured grounding
- User emphasized: must be beginner-friendly and editable
- Agreed to skip: RDF/Turtle, embedding chunks, subgraph chunking

**Research Findings**:
- OG-RAG (Microsoft, EMNLP 2025): JSON-LD is the primary structured grounding format; ontology must be injected in system prompt BEFORE document context
- OntoRAG: Schema Card JSON pattern with `classes`, `datatype_properties`, `object_properties` fields
- TrustGraph: Context engineering with structured Entities/Relationships/Paths sections
- Full JSON-LD compliance unnecessary — "JSON-LD-shaped" dicts are sufficient for LLM consumption (no pyld/rdflib needed)

### Metis Review
**Identified Gaps** (addressed):
- Namespace should be export parameter, NOT Ontology field (avoids breaking `to_dict()`/`from_dict()` contract)
- Each exporter needs `export_FORMAT() -> str` as primary API (string return for LLM injection), with `save_FORMAT()` file wrapper
- Data type mapping needed: `{"string": "xsd:string", "int": "xsd:integer", ...}`
- Edge cases: special chars in URIs need slugification, self-referencing relations, empty ontology, unicode concept names
- Streamlit layout: use `st.expander()` to avoid overflowing sidebar with 5 buttons
- Schema Card: emit empty `events`/`aliases` arrays for OntoRAG compatibility

---

## Work Objectives

### Core Objective
Add three RAG-friendly export formats that let LLMs consume ontologies as domain knowledge, while keeping the output beginner-readable and hand-editable.

### Concrete Deliverables
- `src/ontobuilder/serialization/prompt_io.py` — system prompt text exporter
- `src/ontobuilder/serialization/jsonld_io.py` — JSON-LD exporter
- `src/ontobuilder/serialization/schemacard_io.py` — Schema Card exporter
- `tests/conftest.py` — shared test fixtures
- `tests/test_prompt_export.py` — prompt exporter tests
- `tests/test_jsonld_export.py` — JSON-LD exporter tests
- `tests/test_schemacard_export.py` — Schema Card exporter tests
- Modified `src/ontobuilder/cli/app.py` — 3 new format branches in `export()`
- Modified `streamlit_app.py` — RAG exports expander section

### Definition of Done
- [ ] `pytest tests/ -v` — ALL tests pass (existing + new), zero failures
- [ ] `onto export --format prompt` produces valid readable text with all concepts/relations
- [ ] `onto export --format jsonld` produces valid JSON with `@context`, `@graph`, `@id` on all entities
- [ ] `onto export --format schema-card` produces valid JSON with `classes`, `datatype_properties`, `object_properties`
- [ ] Streamlit app loads without error, RAG export buttons produce correct downloads
- [ ] Empty ontology (zero concepts) produces valid output for all 3 formats (no crashes)

### Must Have
- System prompt export shows concept hierarchy via indentation (children under parents)
- System prompt export shows property types and required flag
- System prompt export shows relation direction with `→` and cardinality
- JSON-LD uses `@id` for every concept/relation (URI-safe slugified names)
- JSON-LD maps `parent` to `rdfs:subClassOf`
- JSON-LD maps properties to `owl:DatatypeProperty` with XSD type ranges
- Schema Card follows OntoRAG structure with `version`, `namespace`, `classes`, `datatype_properties`, `object_properties`
- All exporters handle empty ontology, single-concept ontology, and full ontology
- All outputs are beginner-readable and hand-editable (plain text / indented JSON)

### Must NOT Have (Guardrails)
- Do NOT modify `core/ontology.py`, `core/model.py`, or `core/validation.py` — these are the existing contract
- Do NOT modify existing `json_io.py` or `yaml_io.py`
- Do NOT add any new dependencies to `pyproject.toml` — manual dict construction only
- Do NOT add `load_FORMAT()` / import functions for new formats — export-only
- Do NOT add `namespace` field to Ontology class — namespace is an export parameter only
- Do NOT build a serializer registry/factory pattern — use direct imports like existing code
- Do NOT add RDF/Turtle, embedding chunks, or subgraph chunking — explicitly deferred
- Do NOT use verbose prose in prompt export — structured text with `#`/`##` headers and `-` bullets only
- Do NOT claim W3C JSON-LD compliance — document as "JSON-LD for LLM consumption"

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest, `tests/test_ontology.py`, `tests/test_graph.py`)
- **Automated tests**: TDD (tests first, then implement)
- **Framework**: pytest (already configured in `pyproject.toml`)

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Exporters**: Use Bash (python REPL / pytest) — import, call functions, compare output
- **CLI**: Use Bash — run `onto export --format X`, assert file exists + correct content
- **Streamlit**: Use Bash — `python -c "import streamlit_app"` smoke test (no crash)

### Data Type Mapping Reference (pinned for all exporters)

```python
ONTOBUILDER_TO_XSD = {
    "string": "xsd:string",
    "int": "xsd:integer",
    "float": "xsd:float",
    "bool": "xsd:boolean",
    "date": "xsd:date",
}
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — start immediately):
├── Task 1: Shared test fixtures (conftest.py) [quick]

Wave 2 (Core exporters — MAX PARALLEL after Wave 1):
├── Task 2: System prompt text exporter (TDD) [unspecified-high]
├── Task 3: JSON-LD exporter (TDD) [unspecified-high]
└── Task 4: Schema Card exporter (TDD) [unspecified-high]

Wave 3 (Integration — after Wave 2):
├── Task 5: CLI integration [quick]
└── Task 6: Streamlit UI integration [quick]

Wave FINAL (Verification — after ALL):
├── Task F1: Plan compliance audit [oracle]
├── Task F2: Code quality review [unspecified-high]
├── Task F3: Real QA — all exporters end-to-end [unspecified-high]
└── Task F4: Scope fidelity check [deep]

Critical Path: Task 1 → Task 2/3/4 → Task 5/6 → F1-F4
Parallel Speedup: ~50% faster than sequential
Max Concurrent: 3 (Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 2, 3, 4 | 1 |
| 2 | 1 | 5, 6 | 2 |
| 3 | 1 | 5, 6 | 2 |
| 4 | 1 | 5, 6 | 2 |
| 5 | 2, 3, 4 | F1-F4 | 3 |
| 6 | 2, 3, 4 | F1-F4 | 3 |
| F1-F4 | 5, 6 | — | FINAL |

### Agent Dispatch Summary

- **Wave 1**: 1 task — T1 → `quick`
- **Wave 2**: 3 tasks — T2-T4 → `unspecified-high`
- **Wave 3**: 2 tasks — T5-T6 → `quick`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [ ] 1. Shared Test Fixtures (`conftest.py`)

  **What to do**:
  - Create `tests/conftest.py` with two pytest fixtures:
    - `pet_store_ontology()` — returns a fully populated `Ontology` with: 5+ concepts (including parent-child hierarchy like Animal→Dog→Poodle), 3+ relations (including one self-referencing like `eats: Animal → Animal`), properties with all 5 data types (`string`, `int`, `float`, `bool`, `date`) including at least one `required=True`, 2+ instances with mixed property types
    - `empty_ontology()` — returns `Ontology("Empty")` with zero concepts/relations/instances
  - Run existing tests to verify zero regressions

  **Must NOT do**:
  - Do NOT modify any existing test files
  - Do NOT add any imports to existing tests (they should keep working independently)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file creation, straightforward fixture setup
  - **Skills**: []
    - No special skills needed — standard Python/pytest
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction needed

  **Parallelization**:
  - **Can Run In Parallel**: NO (foundation task)
  - **Parallel Group**: Wave 1 (solo)
  - **Blocks**: Tasks 2, 3, 4
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `tests/test_ontology.py` — Shows existing test style: standalone functions, no classes, direct assertions. New fixtures must be compatible with this style.
  - `tests/test_graph.py:54-64` — Shows `Ontology` construction pattern with `add_concept(parent=...)`, `add_relation()`. Replicate this pattern in fixtures.

  **API/Type References**:
  - `src/ontobuilder/core/ontology.py:29` — `Ontology.add_concept(name, description, parent)` signature
  - `src/ontobuilder/core/ontology.py:72` — `Ontology.add_property(concept_name, prop_name, data_type, required)` signature
  - `src/ontobuilder/core/ontology.py:94` — `Ontology.add_relation(name, source, target, cardinality)` signature
  - `src/ontobuilder/core/ontology.py:123` — `Ontology.add_instance(name, concept, properties)` signature
  - `src/ontobuilder/core/validation.py:37` — `VALID_DATA_TYPES = {"string", "int", "float", "bool", "date"}`

  **Test References**:
  - `tests/test_ontology.py` — Existing tests that MUST still pass after conftest is added

  **External References**:
  - None needed — standard pytest fixtures

  **WHY Each Reference Matters**:
  - `test_ontology.py` style ensures fixtures don't break existing test discovery
  - `validation.py:37` lists all 5 data types — fixture MUST use each one at least once to serve as comprehensive test data
  - `ontology.py` method signatures are the exact API the fixture will call

  **Acceptance Criteria**:

  - [ ] File created: `tests/conftest.py`
  - [ ] `pytest tests/ -v` → ALL existing tests still pass, zero failures
  - [ ] `pet_store_ontology` fixture has ≥5 concepts, ≥3 relations, all 5 data types used, ≥1 required property, ≥2 instances
  - [ ] `empty_ontology` fixture has 0 concepts, 0 relations, 0 instances

  **QA Scenarios**:

  ```
  Scenario: Existing tests still pass with conftest.py present
    Tool: Bash
    Preconditions: conftest.py created in tests/
    Steps:
      1. Run `pytest tests/test_ontology.py tests/test_graph.py tests/test_model.py -v`
      2. Assert exit code 0
      3. Assert output contains "passed" and no "FAILED"
    Expected Result: All pre-existing tests pass unchanged
    Failure Indicators: Any FAILED test, import errors, fixture conflicts
    Evidence: .sisyphus/evidence/task-1-existing-tests-pass.txt

  Scenario: Fixtures are importable and structurally correct
    Tool: Bash
    Preconditions: conftest.py created
    Steps:
      1. Run `python -c "from tests.conftest import pet_store_ontology, empty_ontology; o = pet_store_ontology(); print(len(o.concepts), len(o.relations), len(o.instances))"`
      2. Assert output shows ≥5 concepts, ≥3 relations, ≥2 instances
      3. Run `python -c "from tests.conftest import empty_ontology; o = empty_ontology(); print(len(o.concepts), len(o.relations), len(o.instances))"`
      4. Assert output is `0 0 0`
    Expected Result: pet_store has ≥5/≥3/≥2, empty has 0/0/0
    Failure Indicators: Import error, wrong counts, ValidationError during construction
    Evidence: .sisyphus/evidence/task-1-fixtures-correct.txt
  ```

  **Commit**: YES (commit 1)
  - Message: `test(fixtures): add shared pet_store and empty ontology fixtures`
  - Files: `tests/conftest.py`
  - Pre-commit: `pytest tests/ -v`

---

- [ ] 2. System Prompt Text Exporter (TDD)

  **What to do**:
  - **RED phase**: Create `tests/test_prompt_export.py` with tests for:
    - Full ontology: verifies all concept names appear, hierarchy shown via indentation, properties with types and `(required)` marker, relations with `→` direction and cardinality, `## Concepts` and `## Relations` section headers
    - Empty ontology: produces valid text with ontology name header, no crash, no `## Concepts` / `## Relations` sections when empty
    - Single concept (no parent, no properties, no relations): minimal valid output
    - `include_instances=True`: instances appear in `## Instances` section
    - `include_instances=False` (default): no instances section
    - Concept with unicode name (e.g., `"Üniversité"`): renders correctly
  - **GREEN phase**: Create `src/ontobuilder/serialization/prompt_io.py` with:
    - `export_prompt(onto: Ontology, include_instances: bool = False, max_concepts: int | None = None) -> str` — primary API, returns formatted text string
    - `save_prompt(onto: Ontology, path: str | Path, **kwargs) -> Path` — file-writing wrapper
    - Concept hierarchy built by walking parent→children tree with indentation (2 spaces per level)
    - Properties formatted as: `name (type)` or `name (type, required)`
    - Relations formatted as: `- relation_name: Source → Target (cardinality)`
    - Instances formatted as: `- InstanceName (ConceptName): key=value, key=value`
  - **REFACTOR phase**: Clean up, add docstrings, verify all tests green

  **Target output format** (for pet store example):
  ```
  # Ontology: Pet Store
  A pet store domain model

  ## Concepts
  - Animal: A living creature
    Properties: name (string, required), age (int)
    - Dog: A domestic dog [inherits from Animal]
      Properties: breed (string)
    - Cat: A domestic cat [inherits from Animal]
  - Store: A retail store
  - Customer: A person who buys pets
    Properties: name (string, required)

  ## Relations
  - sold_at: Animal → Store (many-to-many)
  - buys: Customer → Animal (many-to-many)
  ```

  **Must NOT do**:
  - Do NOT use verbose prose — structured text with `#`/`##` headers and `-` bullets only
  - Do NOT show inherited properties (only own properties per concept)
  - Do NOT import or depend on any new packages
  - Do NOT modify any existing files

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: TDD workflow with tree-walking algorithm for hierarchy rendering — moderate complexity
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 4)
  - **Blocks**: Tasks 5, 6
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `src/ontobuilder/serialization/json_io.py:11-17` — Follow this exact function signature pattern: `save_FORMAT(onto: Ontology, path: str | Path) -> Path`
  - `src/ontobuilder/core/ontology.py:157-183` — `print_tree()` method already walks hierarchy. Study its tree-building logic for reference on parent→children traversal.

  **API/Type References**:
  - `src/ontobuilder/core/ontology.py:186-198` — `to_dict()` output shape. Use this to understand what data is available for export.
  - `src/ontobuilder/core/model.py:32-60` — `Concept` dataclass with `name`, `description`, `parent`, `properties` fields
  - `src/ontobuilder/core/model.py:63-90` — `Relation` dataclass with `name`, `source`, `target`, `cardinality`
  - `src/ontobuilder/core/model.py:93-110` — `Instance` dataclass with `name`, `concept`, `properties`

  **Test References**:
  - `tests/test_ontology.py` — Existing test style to follow: standalone functions, direct assertions
  - `tests/conftest.py` (from Task 1) — Use `pet_store_ontology` and `empty_ontology` fixtures

  **External References**:
  - OG-RAG paper: Ontology is injected in system prompt BEFORE document context. This export will be the injection payload.
  - TrustGraph context engineering: Structured text with Entities/Relationships sections.

  **WHY Each Reference Matters**:
  - `json_io.py` provides the exact function signature convention to follow
  - `ontology.py:print_tree()` shows how to walk hierarchy — don't reinvent this logic
  - `model.py` dataclasses define the exact fields available for formatting

  **Acceptance Criteria**:

  - [ ] Test file created: `tests/test_prompt_export.py` with ≥6 test functions
  - [ ] Implementation file created: `src/ontobuilder/serialization/prompt_io.py`
  - [ ] `pytest tests/test_prompt_export.py -v` → ALL pass
  - [ ] `pytest tests/ -v` → ALL pass (zero regressions)
  - [ ] Full ontology output contains all concept names from fixture
  - [ ] Hierarchy shows indentation (children indented under parents)
  - [ ] Properties show `(type)` and `(type, required)` markers
  - [ ] Relations show `→` direction and cardinality
  - [ ] Empty ontology produces valid output without crash

  **QA Scenarios**:

  ```
  Scenario: Full ontology renders readable prompt text
    Tool: Bash
    Preconditions: prompt_io.py implemented, pet_store fixture available
    Steps:
      1. Run `python -c "from tests.conftest import pet_store_ontology; from ontobuilder.serialization.prompt_io import export_prompt; print(export_prompt(pet_store_ontology()))"`
      2. Assert output contains "# Ontology:"
      3. Assert output contains "## Concepts"
      4. Assert output contains "## Relations"
      5. Assert output contains "→"
      6. Assert output contains "(required)"
      7. Assert indentation: child concepts have leading spaces
    Expected Result: Readable structured text with all sections, hierarchy, types
    Failure Indicators: Missing sections, flat hierarchy, missing type annotations
    Evidence: .sisyphus/evidence/task-2-full-ontology-prompt.txt

  Scenario: Empty ontology doesn't crash
    Tool: Bash
    Preconditions: prompt_io.py implemented
    Steps:
      1. Run `python -c "from ontobuilder import Ontology; from ontobuilder.serialization.prompt_io import export_prompt; print(export_prompt(Ontology('Empty')))"`
      2. Assert output contains "# Ontology: Empty"
      3. Assert output does NOT contain "## Concepts"
      4. Assert exit code 0
    Expected Result: Valid minimal output with just the header
    Failure Indicators: Crash, traceback, empty string
    Evidence: .sisyphus/evidence/task-2-empty-ontology-prompt.txt
  ```

  **Commit**: YES (commit 2)
  - Message: `feat(export): add system prompt text exporter with TDD`
  - Files: `src/ontobuilder/serialization/prompt_io.py`, `tests/test_prompt_export.py`
  - Pre-commit: `pytest tests/ -v`

---

- [ ] 3. JSON-LD Exporter (TDD)

  **What to do**:
  - **RED phase**: Create `tests/test_jsonld_export.py` with tests for:
    - Full ontology: `json.loads()` succeeds, has `@context` with `@vocab`/`owl`/`rdfs`/`xsd` prefixes, has `@graph` array, every concept has `@id` and `@type: "owl:Class"`, concepts with parents have `rdfs:subClassOf`, properties mapped to `owl:DatatypeProperty` with XSD ranges, relations mapped to `owl:ObjectProperty`
    - Empty ontology: valid JSON, has `@context` and `@graph` (empty array), no crash
    - Single concept: minimal valid JSON-LD with one node in `@graph`
    - Concept name with spaces (e.g., `"Pet Store"`): `@id` is URI-safe (slugified)
    - Custom namespace parameter: `@vocab` uses provided namespace
    - Default namespace: `@vocab` uses `https://example.org/ontologies/{name}/`
  - **GREEN phase**: Create `src/ontobuilder/serialization/jsonld_io.py` with:
    - `export_jsonld(onto: Ontology, namespace: str | None = None) -> str` — returns JSON string
    - `save_jsonld(onto: Ontology, path: str | Path, **kwargs) -> Path` — file wrapper
    - Slugify function for URI-safe `@id` values: `name.lower().replace(" ", "_")` + strip non-alphanumeric
    - Data type mapping: `ONTOBUILDER_TO_XSD = {"string": "xsd:string", "int": "xsd:integer", "float": "xsd:float", "bool": "xsd:boolean", "date": "xsd:date"}`
    - Concepts → `owl:Class` nodes with `rdfs:label`, `rdfs:comment`, optional `rdfs:subClassOf`
    - Properties → `owl:DatatypeProperty` nodes with `rdfs:domain`, `rdfs:range` (XSD type)
    - Relations → `owl:ObjectProperty` nodes with `rdfs:domain`, `rdfs:range` (concept URI)
    - Instances → individual nodes with `@type` pointing to concept URI, literal property values

  **Must NOT do**:
  - Do NOT add `pyld`, `rdflib`, or any JSON-LD library — manual dict construction only
  - Do NOT claim W3C compliance — document as "JSON-LD for LLM consumption"
  - Do NOT modify any existing files

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: TDD + JSON-LD structure with URI mapping — moderate-to-high complexity
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 2, 4)
  - **Blocks**: Tasks 5, 6
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `src/ontobuilder/serialization/json_io.py:11-17` — Follow function signature pattern. Note `ensure_ascii=False` for unicode support.
  - `src/ontobuilder/core/ontology.py:186-198` — `to_dict()` output shape — this is the data source your exporter will transform

  **API/Type References**:
  - `src/ontobuilder/core/model.py:17-30` — `Property.to_dict()` returns `{"name", "type", "required"}`
  - `src/ontobuilder/core/model.py:41-60` — `Concept.to_dict()` returns `{"name", "description", "parent", "properties"}`
  - `src/ontobuilder/core/model.py:71-90` — `Relation.to_dict()` returns `{"name", "source", "target", "cardinality"}`
  - `src/ontobuilder/core/validation.py:37` — `VALID_DATA_TYPES` — every type here needs an XSD mapping

  **Test References**:
  - `tests/conftest.py` (from Task 1) — Use `pet_store_ontology` and `empty_ontology` fixtures

  **External References**:
  - OG-RAG §4.1.1: JSON-LD is the primary structured grounding format for LLM consumption
  - JSON-LD spec: `@context` with `@vocab` defines default namespace, `@id` for entity URIs, `@type` for class membership

  **WHY Each Reference Matters**:
  - `json_io.py` provides the save function pattern and `ensure_ascii=False` convention
  - `validation.py:37` lists all 5 types that MUST have XSD mappings — missing any = invalid JSON-LD
  - OG-RAG confirms JSON-LD as the right format for the stated use case

  **Acceptance Criteria**:

  - [ ] Test file created: `tests/test_jsonld_export.py` with ≥6 test functions
  - [ ] Implementation file created: `src/ontobuilder/serialization/jsonld_io.py`
  - [ ] `pytest tests/test_jsonld_export.py -v` → ALL pass
  - [ ] `pytest tests/ -v` → ALL pass (zero regressions)
  - [ ] Output is valid JSON (`json.loads()` succeeds)
  - [ ] Output has `@context` with `@vocab`, `owl`, `rdfs`, `xsd` keys
  - [ ] Every concept in `@graph` has `@id` and `@type: "owl:Class"`
  - [ ] Concepts with parents include `rdfs:subClassOf`
  - [ ] Properties include XSD-typed `rdfs:range`
  - [ ] Empty ontology produces valid JSON with empty `@graph`

  **QA Scenarios**:

  ```
  Scenario: JSON-LD is valid and structurally correct
    Tool: Bash
    Preconditions: jsonld_io.py implemented, pet_store fixture available
    Steps:
      1. Run `python -c "from tests.conftest import pet_store_ontology; from ontobuilder.serialization.jsonld_io import export_jsonld; import json; d = json.loads(export_jsonld(pet_store_ontology())); print('@context' in d, '@graph' in d, len(d['@graph']) > 0)"`
      2. Assert output is `True True True`
      3. Run `python -c "from tests.conftest import pet_store_ontology; from ontobuilder.serialization.jsonld_io import export_jsonld; import json; d = json.loads(export_jsonld(pet_store_ontology())); classes = [n for n in d['@graph'] if n.get('@type') == 'owl:Class']; print(all('@id' in c for c in classes), len(classes))"`
      4. Assert all classes have @id and count matches concept count
    Expected Result: Valid JSON-LD with @context, @graph, @id on all entities
    Failure Indicators: json.loads fails, missing @context, missing @id on any entity
    Evidence: .sisyphus/evidence/task-3-jsonld-valid.txt

  Scenario: Empty ontology produces valid JSON-LD
    Tool: Bash
    Preconditions: jsonld_io.py implemented
    Steps:
      1. Run `python -c "from ontobuilder import Ontology; from ontobuilder.serialization.jsonld_io import export_jsonld; import json; d = json.loads(export_jsonld(Ontology('Empty'))); print('@context' in d, '@graph' in d, len(d['@graph']))"`
      2. Assert output is `True True 0`
    Expected Result: Valid JSON with empty @graph array
    Failure Indicators: Crash, invalid JSON, non-empty graph
    Evidence: .sisyphus/evidence/task-3-jsonld-empty.txt
  ```

  **Commit**: YES (commit 3)
  - Message: `feat(export): add JSON-LD exporter with TDD`
  - Files: `src/ontobuilder/serialization/jsonld_io.py`, `tests/test_jsonld_export.py`
  - Pre-commit: `pytest tests/ -v`

---

- [ ] 4. Schema Card Exporter (TDD)

  **What to do**:
  - **RED phase**: Create `tests/test_schemacard_export.py` with tests for:
    - Full ontology: `json.loads()` succeeds, has `version` (ISO timestamp), `namespace`, `classes` (count matches concepts), `datatype_properties` (count matches total properties across concepts), `object_properties` (count matches relations), `events: []`, `aliases: []`, `warnings` array
    - Empty ontology: valid JSON, all arrays empty, has `version` and `namespace`
    - Warnings populated: concept without description triggers warning in `warnings` array
    - Custom namespace: namespace parameter overrides default
    - Each class entry has `name`, `description`, `origin: "defined"` fields
    - Each property entry has `name`, `domain`, `range`, `description`, `origin` fields
  - **GREEN phase**: Create `src/ontobuilder/serialization/schemacard_io.py` with:
    - `export_schema_card(onto: Ontology, namespace: str | None = None) -> str` — returns JSON string
    - `save_schema_card(onto: Ontology, path: str | Path, **kwargs) -> Path` — file wrapper
    - Type mapping: `ONTOBUILDER_TO_SCHEMACARD = {"string": "string", "int": "integer", "float": "number", "bool": "boolean", "date": "date"}`
    - Concepts → `classes` array entries
    - Properties → `datatype_properties` array entries (flattened from all concepts)
    - Relations → `object_properties` array entries
    - `events: []`, `aliases: []` — always empty (no model counterpart)
    - `warnings` — populated with validation notes (e.g., concept with no description, relation with default cardinality)

  **Must NOT do**:
  - Do NOT invent data for `events` or `aliases` — always empty arrays
  - Do NOT add any new dependencies
  - Do NOT modify any existing files

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: TDD + OntoRAG-compatible structure with warnings logic — moderate complexity
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 2, 3)
  - **Blocks**: Tasks 5, 6
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `src/ontobuilder/serialization/json_io.py:11-17` — Follow function signature pattern
  - `src/ontobuilder/core/ontology.py:186-198` — `to_dict()` as data source

  **API/Type References**:
  - `src/ontobuilder/core/model.py:32-60` — `Concept` with `properties` list — each property must become a `datatype_properties` entry with `domain` = concept name
  - `src/ontobuilder/core/model.py:63-90` — `Relation` → `object_properties` entry
  - `src/ontobuilder/core/validation.py:37` — Data types for range mapping

  **Test References**:
  - `tests/conftest.py` (from Task 1) — Use fixtures

  **External References**:
  - OntoRAG Schema Card structure: `version`, `namespace`, `classes[{name, description, origin}]`, `datatype_properties[{name, domain, range, description, origin}]`, `object_properties[{name, domain, range, description, origin}]`, `events[]`, `aliases[]`, `warnings[]`

  **WHY Each Reference Matters**:
  - OntoRAG Schema Card is the exact target format — deviating breaks compatibility with OntoRAG consumers
  - `model.py` field names map directly to Schema Card fields (concept.name → class.name, etc.)

  **Acceptance Criteria**:

  - [ ] Test file created: `tests/test_schemacard_export.py` with ≥6 test functions
  - [ ] Implementation file created: `src/ontobuilder/serialization/schemacard_io.py`
  - [ ] `pytest tests/test_schemacard_export.py -v` → ALL pass
  - [ ] `pytest tests/ -v` → ALL pass (zero regressions)
  - [ ] Output has `version`, `namespace`, `classes`, `datatype_properties`, `object_properties`, `events`, `aliases`, `warnings`
  - [ ] `classes` count matches concept count
  - [ ] `events` and `aliases` are always empty arrays
  - [ ] Concept without description generates a warning

  **QA Scenarios**:

  ```
  Scenario: Schema Card has correct OntoRAG structure
    Tool: Bash
    Preconditions: schemacard_io.py implemented, pet_store fixture available
    Steps:
      1. Run `python -c "from tests.conftest import pet_store_ontology; from ontobuilder.serialization.schemacard_io import export_schema_card; import json; d = json.loads(export_schema_card(pet_store_ontology())); print(sorted(d.keys()))"`
      2. Assert output contains: aliases, classes, datatype_properties, events, namespace, object_properties, version, warnings
      3. Run `python -c "from tests.conftest import pet_store_ontology; from ontobuilder.serialization.schemacard_io import export_schema_card; import json; d = json.loads(export_schema_card(pet_store_ontology())); print(d['events'], d['aliases'])"`
      4. Assert both are `[] []`
    Expected Result: All required keys present, events/aliases always empty
    Failure Indicators: Missing keys, non-empty events/aliases, json.loads fails
    Evidence: .sisyphus/evidence/task-4-schemacard-structure.txt

  Scenario: Empty ontology produces valid Schema Card
    Tool: Bash
    Preconditions: schemacard_io.py implemented
    Steps:
      1. Run `python -c "from ontobuilder import Ontology; from ontobuilder.serialization.schemacard_io import export_schema_card; import json; d = json.loads(export_schema_card(Ontology('Empty'))); print(len(d['classes']), len(d['datatype_properties']), len(d['object_properties']))"`
      2. Assert output is `0 0 0`
    Expected Result: Valid JSON with all empty arrays
    Failure Indicators: Crash, invalid JSON
    Evidence: .sisyphus/evidence/task-4-schemacard-empty.txt
  ```

  **Commit**: YES (commit 4)
  - Message: `feat(export): add Schema Card exporter with TDD`
  - Files: `src/ontobuilder/serialization/schemacard_io.py`, `tests/test_schemacard_export.py`
  - Pre-commit: `pytest tests/ -v`

- [ ] 5. CLI Integration — Add New Export Formats

  **What to do**:
  - Modify `src/ontobuilder/cli/app.py` in the `export()` function (lines 93-114):
    - Update `format` parameter help text (line 95) from `"Export format: yaml or json"` to `"Export format: yaml, json, prompt, jsonld, or schema-card"`
    - Add `elif format == "prompt":` branch that calls `save_prompt(onto, out)` with default filename `ontology.prompt.txt`
    - Add `elif format == "jsonld":` branch that calls `save_jsonld(onto, out)` with default filename `ontology.jsonld`
    - Add `elif format == "schema-card":` branch that calls `save_schema_card(onto, out)` with default filename `ontology.schema-card.json`
    - Update the `else` error message (line 112) to list all 5 available formats
    - Add lazy imports at the top of each branch (matching existing pattern of importing inside function)

  **Must NOT do**:
  - Do NOT refactor the if/elif chain into a registry — keep existing pattern
  - Do NOT modify any other CLI commands
  - Do NOT modify serialization files from Tasks 2-4

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Adding elif branches to an existing function — straightforward modification
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 6)
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 2, 3, 4

  **References**:

  **Pattern References**:
  - `src/ontobuilder/cli/app.py:93-114` — The exact function to modify. Follow the existing `if format == "json"` / `elif format == "yaml"` pattern exactly.
  - `src/ontobuilder/cli/app.py:64-71` — `save()` command shows the pattern of lazy imports inside function body

  **API/Type References**:
  - `src/ontobuilder/serialization/prompt_io.py` (from Task 2) — `save_prompt(onto, path) -> Path`
  - `src/ontobuilder/serialization/jsonld_io.py` (from Task 3) — `save_jsonld(onto, path) -> Path`
  - `src/ontobuilder/serialization/schemacard_io.py` (from Task 4) — `save_schema_card(onto, path) -> Path`

  **WHY Each Reference Matters**:
  - `app.py:93-114` is the exact code being modified — must match its style perfectly
  - Save function signatures from Tasks 2-4 are the APIs being called

  **Acceptance Criteria**:

  - [ ] `onto export --format prompt` produces `ontology.prompt.txt`
  - [ ] `onto export --format jsonld` produces `ontology.jsonld`
  - [ ] `onto export --format schema-card` produces `ontology.schema-card.json`
  - [ ] `onto export --format invalid` shows error listing all 5 formats
  - [ ] `onto export --help` shows updated format list
  - [ ] `pytest tests/ -v` → ALL pass (zero regressions)

  **QA Scenarios**:

  ```
  Scenario: All 3 new export formats work via CLI
    Tool: Bash
    Preconditions: Ontology file exists in working directory (run `onto init "Test"` + add concepts first)
    Steps:
      1. Create temp directory, cd into it
      2. Run `onto init "Test" && onto concept add Animal --description "A creature"`
      3. Run `onto export --format prompt` → assert `ontology.prompt.txt` exists
      4. Run `onto export --format jsonld` → assert `ontology.jsonld` exists
      5. Run `onto export --format schema-card` → assert `ontology.schema-card.json` exists
      6. Verify each file is non-empty and contains expected content
    Expected Result: All 3 files created with correct content
    Failure Indicators: File not created, empty file, import error, wrong format
    Evidence: .sisyphus/evidence/task-5-cli-export-formats.txt

  Scenario: Invalid format shows helpful error
    Tool: Bash
    Preconditions: Ontology file exists
    Steps:
      1. Run `onto export --format invalid` and capture stderr/stdout
      2. Assert output contains "yaml" AND "json" AND "prompt" AND "jsonld" AND "schema-card"
    Expected Result: Error message lists all 5 available formats
    Failure Indicators: Generic error, missing format names
    Evidence: .sisyphus/evidence/task-5-cli-error-message.txt
  ```

  **Commit**: YES (commit 5)
  - Message: `feat(cli): add prompt, jsonld, schema-card to export command`
  - Files: `src/ontobuilder/cli/app.py`
  - Pre-commit: `pytest tests/ -v`

---

- [ ] 6. Streamlit UI — RAG Exports Section

  **What to do**:
  - Modify `streamlit_app.py` to add a RAG exports section after the existing Import/Export area (after line 160):
    - Add `st.divider()` followed by `st.subheader("RAG Exports")`
    - Inside an `st.expander("Export for LLM / RAG", expanded=False)`:
      - Add `st.download_button` for "System Prompt (.txt)" calling `export_prompt(onto)`
      - Add `st.download_button` for "JSON-LD (.jsonld)" calling `export_jsonld(onto)`
      - Add `st.download_button` for "Schema Card (.json)" calling `export_schema_card(onto)`
    - Add brief helper text: `st.caption("Export your ontology in formats optimized for LLM consumption")`
    - Use lazy imports (matching existing pattern): `from ontobuilder.serialization.prompt_io import export_prompt` etc.

  **Must NOT do**:
  - Do NOT move or modify existing download buttons (YAML/JSON at lines 157-160)
  - Do NOT add the buttons directly in sidebar columns — use `st.expander()` to avoid layout overflow
  - Do NOT modify any serialization files

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Adding download buttons to existing UI — straightforward Streamlit pattern
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: Could be used for visual QA but overkill for download buttons
    - `frontend-ui-ux`: Streamlit is not a frontend framework

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 5)
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 2, 3, 4

  **References**:

  **Pattern References**:
  - `streamlit_app.py:154-160` — Existing download buttons pattern. Follow exact same `st.download_button()` call style.
  - `streamlit_app.py:1-10` — Existing imports pattern for the file

  **API/Type References**:
  - `src/ontobuilder/serialization/prompt_io.py` (from Task 2) — `export_prompt(onto) -> str`
  - `src/ontobuilder/serialization/jsonld_io.py` (from Task 3) — `export_jsonld(onto) -> str`
  - `src/ontobuilder/serialization/schemacard_io.py` (from Task 4) — `export_schema_card(onto) -> str`

  **WHY Each Reference Matters**:
  - `streamlit_app.py:154-160` shows the exact pattern for download buttons in sidebar — replicate this
  - Export functions return strings which feed directly into `st.download_button(data=...)`

  **Acceptance Criteria**:

  - [ ] RAG exports section visible in Streamlit sidebar
  - [ ] 3 download buttons present: System Prompt, JSON-LD, Schema Card
  - [ ] `python -c "import streamlit_app"` → no import crash
  - [ ] `pytest tests/ -v` → ALL pass (zero regressions)

  **QA Scenarios**:

  ```
  Scenario: Streamlit app imports without crash
    Tool: Bash
    Preconditions: streamlit_app.py modified with RAG exports section
    Steps:
      1. Run `python -c "import streamlit_app; print('OK')"`
      2. Assert output is "OK"
      3. Assert exit code 0
    Expected Result: No import errors, no crash
    Failure Indicators: ImportError, AttributeError, any traceback
    Evidence: .sisyphus/evidence/task-6-streamlit-import.txt

  Scenario: RAG export code is syntactically present
    Tool: Bash
    Preconditions: streamlit_app.py modified
    Steps:
      1. Search streamlit_app.py for "RAG Exports" or "RAG" header text
      2. Search for "export_prompt" import/usage
      3. Search for "export_jsonld" import/usage
      4. Search for "export_schema_card" import/usage
      5. Search for "st.download_button" calls (should be ≥5 total: 2 existing + 3 new)
    Expected Result: All 3 new export functions referenced, all download buttons present
    Failure Indicators: Missing function references, fewer than 5 download buttons
    Evidence: .sisyphus/evidence/task-6-streamlit-code-check.txt
  ```

  **Commit**: YES (commit 6)
  - Message: `feat(ui): add RAG exports section to Streamlit sidebar`
  - Files: `streamlit_app.py`
  - Pre-commit: `pytest tests/ -v`

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest tests/ -v`. Review all new files for: `as any`/`@ts-ignore` equivalents, empty catches, print statements in library code, unused imports. Check AI slop: excessive comments, over-abstraction, generic variable names. Verify all new functions have docstrings.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real QA — All Exporters End-to-End** — `unspecified-high`
  Start from clean state. Build a pet store ontology via API. Run all 3 exporters. Verify: prompt text is human-readable and correctly indented, JSON-LD parses as valid JSON with all `@id`/`@type`/`@context` present, Schema Card matches OntoRAG structure. Test empty ontology case. Test CLI `onto export --format prompt|jsonld|schema-card`. Save evidence to `.sisyphus/evidence/final-qa/`.
  Output: `Exporters [3/3 pass] | Edge Cases [N/N] | CLI [3/3] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT Have" compliance: no changes to `core/ontology.py`, `core/model.py`, `core/validation.py`, `json_io.py`, `yaml_io.py`. No new dependencies in `pyproject.toml`. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Forbidden Files [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

| # | Message | Files | Pre-commit |
|---|---------|-------|------------|
| 1 | `test(fixtures): add shared pet_store and empty ontology fixtures` | `tests/conftest.py` | `pytest tests/ -v` |
| 2 | `feat(export): add system prompt text exporter with TDD` | `src/ontobuilder/serialization/prompt_io.py`, `tests/test_prompt_export.py` | `pytest tests/ -v` |
| 3 | `feat(export): add JSON-LD exporter with TDD` | `src/ontobuilder/serialization/jsonld_io.py`, `tests/test_jsonld_export.py` | `pytest tests/ -v` |
| 4 | `feat(export): add Schema Card exporter with TDD` | `src/ontobuilder/serialization/schemacard_io.py`, `tests/test_schemacard_export.py` | `pytest tests/ -v` |
| 5 | `feat(cli): add prompt, jsonld, schema-card to export command` | `src/ontobuilder/cli/app.py` | `pytest tests/ -v` |
| 6 | `feat(ui): add RAG exports section to Streamlit sidebar` | `streamlit_app.py` | `pytest tests/ -v` |

---

## Success Criteria

### Verification Commands
```bash
pytest tests/ -v                              # Expected: ALL PASS, 0 failures
python -c "from ontobuilder.serialization.prompt_io import export_prompt; print('OK')"    # Expected: OK
python -c "from ontobuilder.serialization.jsonld_io import export_jsonld; print('OK')"    # Expected: OK
python -c "from ontobuilder.serialization.schemacard_io import export_schema_card; print('OK')"  # Expected: OK
python -c "import streamlit_app; print('OK')"  # Expected: OK (no import crash)
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] Zero new dependencies in pyproject.toml
- [ ] All 3 export formats produce valid output for empty + full ontologies
- [ ] CLI help text lists all 5 formats
- [ ] Streamlit RAG exports section renders without error
