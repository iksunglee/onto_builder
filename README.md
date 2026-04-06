# OntoBuilder

Build small, understandable ontologies from scratch or from data, then inspect, refine, and export them without needing to know OWL up front.

OntoBuilder is a Python toolkit for creating ontologies with concepts, properties, relations, and instances. It ships with a CLI, a Python API, OWL/RDF export, lightweight reasoning, data-to-ontology helpers, optional AI-assisted workflows, and a Streamlit app for visual editing.

## What To Expect

- Good fit for: learning ontology modeling, prototyping domain models, turning CSV/JSON structure into a first ontology draft, exporting to OWL/Turtle/JSON-LD, and iterating from the terminal or Python.
- Core workflows work locally: create an ontology, edit it, save it as `.onto.yaml`, inspect it, export it, and run basic reasoning checks.
- AI features are optional: interview mode, inference from sample data, and the live workspace need LLM dependencies and provider setup.
- The project is still early-stage: useful already, but expect some rough edges around advanced flows and docs.

## Main Ways To Use It

### 1. CLI

The installed command is `ontobuilder`.

You can also run the module form:

```bash
python -m ontobuilder
```

Use the CLI when you want to:

- create and save an ontology project
- add concepts, relations, and properties from the terminal
- export to YAML, JSON, prompt text, JSON-LD, Schema Card, OWL, or Turtle
- run reasoning and structured queries
- build from data or use the AI-assisted workspace

### 2. Python API

Use the Python API when you want to script ontology creation directly inside your application or notebook.

### 3. Streamlit App

Use the web UI when you want a more visual editing flow with graph views and guided next steps.

## Installation

```bash
# Core package
pip install ontobuilder

# AI-assisted features
pip install ontobuilder[llm]

# Streamlit app
pip install ontobuilder[web]

# Everything
pip install ontobuilder[all]
```

For local development:

```bash
git clone https://github.com/iksun/ontobuilder.git
cd ontobuilder
pip install -e ".[dev,llm,web]"
```

## Quick Start

### Python API

```python
from ontobuilder import Ontology

onto = Ontology("Pet Store", description="A simple pet store ontology")

onto.add_concept("Animal", description="A living creature")
onto.add_concept("Dog", parent="Animal", description="A domestic dog")
onto.add_concept("Customer", description="A person who buys pets")

onto.add_property("Animal", "name", data_type="string", required=True)
onto.add_property("Dog", "breed", data_type="string")

onto.add_relation("buys", source="Customer", target="Animal")

onto.add_instance("Rex", concept="Dog", properties={"name": "Rex", "breed": "Labrador"})

print(onto.print_tree())
```

### CLI Basics

```bash
ontobuilder init "Hospital Booking"
ontobuilder concept add Patient --description "A person receiving care"
ontobuilder concept add Surgeon
ontobuilder concept add SurgeryBooking
ontobuilder relation add assigned_surgeon --from SurgeryBooking --to Surgeon
ontobuilder info
ontobuilder owl export --format turtle
ontobuilder owl reason
ontobuilder owl query describe SurgeryBooking
```

### Build From Data

```bash
ontobuilder tool analyze data.csv
ontobuilder tool suggest data.csv
ontobuilder tool build data.csv
ontobuilder tool build -i data.csv
```

What this flow gives you:

- `analyze` shows the structure OntoBuilder sees in the file
- `suggest` proposes concepts and relations
- `build` creates an ontology draft
- `build -i` lets you review suggestions step by step

### AI-Assisted Workflows

First configure an LLM provider:

```bash
ontobuilder configure
```

Then you can use:

```bash
ontobuilder interview
ontobuilder infer data.csv            # AI-powered
ontobuilder infer data.csv --local    # offline, no API key; launches interactive review
ontobuilder workspace data.csv
```

Use these when you want:

- `interview` - guided ontology design through questions
- `infer` - a quick AI-generated ontology draft from data
- `workspace` - data -> ontology draft -> chat refinement -> OWL export

### Web UI

```bash
pip install ontobuilder[web]
streamlit run streamlit_app.py
```

The app includes concept editing, graph visualization, CSV-assisted ontology building, next-step suggestions, and chat-based exploration.

## CLI Command Map

| Command | What it does |
|---------|---------------|
| `ontobuilder init` | Create a new ontology file in the current directory |
| `ontobuilder info` | Show summary information about the current ontology |
| `ontobuilder concept add/list/remove` | Manage concepts |
| `ontobuilder relation add/list/remove` | Manage relations |
| `ontobuilder save` / `ontobuilder load` | Save or load `.onto.yaml` files |
| `ontobuilder export` | Export to `yaml`, `json`, `prompt`, `jsonld`, `schema-card`, `owl`, or `turtle` |
| `ontobuilder owl export` | Export OWL as RDF/XML or Turtle |
| `ontobuilder owl reason` | Run inference and consistency checks |
| `ontobuilder owl query` | Query classes, instances, relations, descriptions, validation, or paths |
| `ontobuilder tool analyze` | Inspect a data file |
| `ontobuilder tool suggest` | Generate ontology suggestions from data |
| `ontobuilder tool build` | Build an ontology from data |
| `ontobuilder suggest` | Suggest likely next steps for the current ontology |
| `ontobuilder learn` | Show glossary-style explanations of ontology terms |
| `ontobuilder domains list/apply` | List and apply built-in domain templates |
| `ontobuilder configure` | Configure an LLM provider |
| `ontobuilder interview` | Build an ontology through an AI-assisted interview |
| `ontobuilder infer` | Infer an ontology draft from a data file (use `--local` for offline interactive review) |
| `ontobuilder chat` | Ask questions about the current ontology |
| `ontobuilder workspace` | Open a live AI-assisted ontology workspace |

## Files You Will See

- `ontology.onto.yaml` - the default working ontology file used by the CLI
- `ontology.ttl` / `ontology.owl` - common export outputs
- your source CSV/JSON files - optional inputs for data-assisted modeling

## Architecture At A Glance

```text
src/ontobuilder/
|- core/           # Ontology model, concepts, properties, relations, validation
|- cli/            # Typer-based CLI
|- serialization/  # YAML, JSON, JSON-LD, Schema Card, prompt export
|- owl/            # OWL/Turtle export, reasoning, structured query support
|- llm/            # Optional LLM-backed inference and interview flows
|- chat/           # Ontology chat and workspace flows
|- tool/           # Data analysis and ontology suggestion pipeline
|- graph/          # NetworkX and optional Neo4j utilities
|- domains/        # Built-in domain templates
`- education/      # Beginner glossary and learning helpers
```

## Examples

See the `examples/` directory for starter files and datasets.

Useful starting points:

- `examples/quickstart.py` - basic Python API walkthrough
- `examples/hospital_surgery_booking.onto.yaml` - example ontology file
- `examples/hospital_surgery_bookings.csv` - sample input dataset
- `examples/real_ecommerce_orders.csv` - e-commerce-style dataset

Example commands:

```bash
python examples/quickstart.py
ontobuilder tool build -i examples/hospital_surgery_bookings.csv
```

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE)
