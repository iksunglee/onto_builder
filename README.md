# OntoBuilder

**Build, explore, and export ontologies from data — no PhD required.**

OntoBuilder is a Python toolkit that turns raw data (CSV, JSON) into formal ontologies with concepts, relations, properties, and standards-compliant exports. It is designed to bridge the gap between your data and the structured knowledge that LLMs need to reason accurately about your domain.

Whether you're grounding a Claude assistant with your company's data model, building a RAG pipeline with structured schema context, or exporting OWL ontologies for the semantic web — OntoBuilder gets you there from a single CSV file.

---

## Why OntoBuilder?

LLMs are powerful, but they hallucinate when they don't understand your domain. OntoBuilder solves this by letting you:

1. **Define your domain formally** — concepts, properties, relations, and hierarchy
2. **Export as LLM-ready formats** — system prompt text, JSON-LD, and Schema Card
3. **Inject domain knowledge into any LLM** — Claude, GPT, Gemini, or open-source models
4. **Use AI to help build the ontology itself** — interview mode, data inference, and chat-based refinement

The result: LLMs that understand your domain's vocabulary, constraints, and relationships — not just keywords.

---

## Features

- **Data → Ontology pipeline** — analyze CSV/JSON files, get concept and relation suggestions, build ontologies automatically or interactively
- **Rich CLI** — manage concepts, properties, relations, instances, and exports from the terminal
- **OWL/RDF export** — Turtle and RDF-XML via rdflib, with built-in reasoning and consistency checks
- **RAG-friendly exports** — JSON-LD, Schema Card, and system prompt text formats designed for LLM consumption
- **LLM integration** — AI-powered interview mode, natural language chat, and structure inference (Claude, OpenAI, and 100+ models via LiteLLM)
- **Domain templates** — pre-built starters for healthcare, e-commerce, and more
- **Web UI** — visual ontology builder with Streamlit
- **Graph backends** — NetworkX (built-in) and Neo4j
- **Educational glossary** — learn ontology terms as you build

---

## Installation

```bash
# Core (CLI + OWL export + reasoning)
pip install ontobuilder

# With OpenAI support (lightweight)
pip install ontobuilder[openai]

# With multi-provider LLM support (Claude, GPT, Gemini, etc.)
pip install ontobuilder[llm]

# With web UI
pip install ontobuilder[web]

# Everything
pip install ontobuilder[all]
```

For development:

```bash
git clone https://github.com/iksunglee/onto_builder.git
cd onto_builder
pip install -e ".[dev,llm,web]"
```

---

## Quick Start

### Python API

```python
from ontobuilder import Ontology

onto = Ontology("Pet Store", description="A pet store domain model")

# Add concepts with hierarchy
onto.add_concept("Animal", description="A living creature")
onto.add_concept("Dog", parent="Animal", description="A domestic dog")
onto.add_concept("Cat", parent="Animal", description="A domestic cat")
onto.add_concept("Customer", description="A person who buys pets")

# Add properties
onto.add_property("Animal", "name", data_type="string", required=True)
onto.add_property("Animal", "age", data_type="int")
onto.add_property("Dog", "breed", data_type="string")

# Add relations
onto.add_relation("buys", source="Customer", target="Animal")

# Add instances
onto.add_instance("Rex", concept="Dog", properties={"name": "Rex", "breed": "Labrador"})

print(onto.print_tree())
```

### CLI

```bash
# Create a new ontology
onto init "Hospital Booking"

# Add concepts
onto concept add Patient --description "A person receiving care"
onto concept add Surgeon --parent Provider
onto concept add SurgeryBooking

# Add relations
onto relation add assigned_surgeon --source SurgeryBooking --target Surgeon

# View the ontology
onto info

# Export
onto export --format prompt     # LLM system prompt text
onto export --format jsonld     # JSON-LD for structured grounding
onto export --format schema-card # Schema Card for RAG pipelines
onto owl export --format turtle  # OWL/RDF for semantic web
```

### Build from Data

```bash
# Analyze a data file
onto tool analyze data.csv

# Get ontology suggestions
onto tool suggest data.csv

# Auto-build ontology from data
onto tool build data.csv

# Interactive mode — review each suggestion step by step
onto tool build -i data.csv
```

---

## Using OntoBuilder with LLMs

OntoBuilder is designed to produce ontology exports that you can feed directly to LLMs as context. This section shows how to use OntoBuilder with **Claude** and **OpenAI GPT** models.

### Export Formats for LLM Consumption

OntoBuilder provides three export formats optimized for LLM use:

| Format | Best For | Command |
|--------|----------|---------|
| **System Prompt Text** | Direct injection into system prompts | `onto export --format prompt` |
| **JSON-LD** | Structured grounding, semantic search | `onto export --format jsonld` |
| **Schema Card** | RAG pipelines, OntoRAG integration | `onto export --format schema-card` |

### 1. System Prompt Text — Inject Domain Knowledge Directly

The `prompt` export produces human-readable structured text that you can paste directly into a system prompt.

```bash
onto export --format prompt -o my_domain.prompt.txt
```

Output example:

```
# Ontology: Hospital Booking
Operating room booking and allocation

## Concepts
- Patient: A person receiving surgery
  Properties: patient_id (string) (required), name (string)
  - Inpatient: A patient admitted to hospital [inherits from Patient]
- SurgeryBooking: A scheduled surgery
  Properties: booking_date (date) (required), status (string)

## Relations
- booked_for_patient: SurgeryBooking → Patient (many-to-one)
- assigned_surgeon: SurgeryBooking → Surgeon (many-to-one)
```

#### Use with Claude (Anthropic API)

```python
import anthropic
from ontobuilder import Ontology
from ontobuilder.serialization.prompt_io import export_prompt

# Load your ontology
onto = Ontology.from_file("hospital.onto.yaml")
domain_context = export_prompt(onto)

# Use as system prompt context
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system=f"""You are a hospital booking assistant. Use the following domain model
to understand the entities and relationships in our system. Always use the correct
terminology and respect the constraints defined below.

{domain_context}""",
    messages=[
        {"role": "user", "content": "Can a surgery booking have multiple surgeons?"}
    ]
)
print(response.content[0].text)
# Claude will reference the ontology: "Based on the domain model, the
# assigned_surgeon relation is many-to-one, meaning each SurgeryBooking
# has exactly one Surgeon..."
```

#### Use with OpenAI GPT

```python
from openai import OpenAI
from ontobuilder import Ontology
from ontobuilder.serialization.prompt_io import export_prompt

onto = Ontology.from_file("hospital.onto.yaml")
domain_context = export_prompt(onto)

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": f"You are a hospital booking assistant.\n\n{domain_context}"
        },
        {
            "role": "user",
            "content": "What information is required to create a surgery booking?"
        }
    ]
)
print(response.choices[0].message.content)
```

### 2. JSON-LD — Structured Grounding for RAG

The `jsonld` export produces semantic web-compatible JSON that works well as structured context in retrieval-augmented generation pipelines.

```bash
onto export --format jsonld -o my_domain.jsonld.json
```

```python
from ontobuilder import Ontology
from ontobuilder.serialization.jsonld_io import export_jsonld

onto = Ontology.from_file("hospital.onto.yaml")
jsonld = export_jsonld(onto)

# Use as structured context in your RAG pipeline
# The JSON-LD includes @context, owl:Class definitions,
# owl:DatatypeProperty, and owl:ObjectProperty — all parseable
# by both LLMs and semantic web tools.
```

### 3. Schema Card — RAG Pipeline Integration

The Schema Card format is designed for OntoRAG and similar schema-aware retrieval systems.

```bash
onto export --format schema-card -o my_domain.schema-card.json
```

```python
from ontobuilder import Ontology
from ontobuilder.serialization.schemacard_io import export_schema_card

onto = Ontology.from_file("hospital.onto.yaml")
card = export_schema_card(onto)

# Feed into your RAG pipeline as schema context
# Includes: classes, datatype_properties, object_properties,
# events, aliases, and validation warnings
```

### 4. OWL/RDF — Standards-Compliant Exports

For integration with knowledge graph platforms, SPARQL endpoints, or any semantic web tool:

```bash
onto owl export --format turtle -o my_domain.ttl
onto owl export --format xml -o my_domain.owl
```

---

## AI-Powered Ontology Building

OntoBuilder can use LLMs to **help you build** ontologies, not just consume them. This works with Claude (via LiteLLM) or OpenAI directly.

### Configuration

```bash
# Option A: Use OpenAI directly (lightweight)
export OPENAI_API_KEY=sk-...
export ONTOBUILDER_LLM_MODEL=gpt-4o-mini    # optional, this is the default

# Option B: Use Claude via LiteLLM (requires ontobuilder[llm])
export ANTHROPIC_API_KEY=sk-ant-...
export ONTOBUILDER_LLM_MODEL=anthropic/claude-sonnet-4-20250514

# Option C: Use any LiteLLM-supported provider
export ONTOBUILDER_LLM_MODEL=gemini/gemini-2.0-flash
export ONTOBUILDER_LLM_BACKEND=litellm      # force litellm backend
```

Or configure via CLI:

```bash
onto configure --api-key sk-... --model gpt-4o-mini
onto configure --show  # verify current settings
```

### Interview Mode — AI Asks the Right Questions

Let the LLM guide you through building an ontology from scratch by asking domain-specific questions:

```bash
onto interview --domain healthcare
```

The AI will:
1. Ask scoping questions about your domain
2. Suggest concepts based on your answers
3. Propose relations between concepts
4. Build the ontology from your confirmed selections

### Data Inference — From CSV to Ontology in Seconds

Point the AI at your data and let it infer the ontology structure:

```bash
onto infer data.csv
```

The LLM analyzes column names, types, and patterns to suggest concepts, properties, and relations.

### Chat — Refine Your Ontology Conversationally

```bash
# Interactive chat session
onto chat

# Single question
onto chat "What concepts am I missing for a complete e-commerce model?"
```

### Workspace — Full Data-to-Ontology Pipeline

The workspace combines everything: analyze data, infer structure, chat to refine, and export — all in one session:

```bash
onto workspace data.csv
```

Built-in workspace commands:
- `show` — display current ontology state
- `tree` — show class hierarchy
- `check` — run consistency checks
- `owl` — preview OWL output
- `log` — show edit history
- `save` — export to file

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `onto init` | Create a new ontology project |
| `onto info` | Show ontology summary |
| `onto concept add/list/remove` | Manage concepts |
| `onto relation add/list/remove` | Manage relations |
| `onto save / load` | Save or load `.onto.yaml` files |
| `onto export` | Export to various formats |
| `onto owl export` | Export as OWL/RDF (Turtle or RDF-XML) |
| `onto owl reason` | Run OWL inference and consistency checks |
| `onto owl query` | Structured queries (classes, relations, describe, path) |
| `onto tool analyze` | Analyze a data file |
| `onto tool suggest` | Show ontology suggestions from data |
| `onto tool build` | Build ontology from data (auto or interactive) |
| `onto interview` | AI-powered interview to build an ontology |
| `onto infer` | Auto-infer ontology from data using LLM |
| `onto chat` | Chat with your ontology in natural language |
| `onto workspace` | Full workspace: analyze, build, chat, export |
| `onto learn` | Learn ontology terms |
| `onto suggest` | Get next-step suggestions |
| `onto domains list/apply` | Browse and apply domain templates |
| `onto configure` | Set up LLM API keys and models |

---

## Architecture

```
src/ontobuilder/
├── core/           # Data model — Concept, Property, Relation, Instance, Ontology
├── cli/            # Typer CLI with Rich formatting
├── serialization/  # YAML, JSON, JSON-LD, Schema Card, Prompt exporters
├── owl/            # OWL/RDF export, reasoning, structured queries (rdflib)
├── llm/            # LLM integration (LiteLLM, OpenAI, Instructor)
├── chat/           # Natural language chat and workspace
├── tool/           # Data analysis → ontology building pipeline
├── graph/          # Graph backends (NetworkX, Neo4j)
├── domains/        # Domain templates (healthcare, e-commerce)
└── education/      # Ontology glossary for beginners
```

---

## Examples

See the [`examples/`](examples/) directory:

| File | Description |
|------|-------------|
| `quickstart.py` | Build a Pet Store ontology with the Python API |
| `hospital_surgery_booking.onto.yaml` | Hospital surgery booking ontology |
| `hospital_surgery_bookings.csv` | Sample hospital surgery data |
| `real_ecommerce_orders.csv` | E-commerce orders dataset |
| `bookstore.csv` | Bookstore dataset |
| `concept_university.csv` | University concepts dataset |

```bash
# Run the quickstart
python examples/quickstart.py

# Build from hospital data
onto tool build -i examples/hospital_surgery_bookings.csv
```

---

## Web UI

```bash
pip install ontobuilder[web]
streamlit run streamlit_app.py
```

The Streamlit UI provides visual graph rendering, drag-and-drop ontology editing, domain template browsing, chat integration, and one-click exports.

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

---

## License

[MIT](LICENSE)
