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

The installed command is `onto`.

If you prefer, you can also run the module form:

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
# The CLI command is `onto`
onto init "Hospital Booking"
onto concept add Patient --description "A person receiving care"
onto concept add Surgeon
onto concept add SurgeryBooking
onto relation add assigned_surgeon --source SurgeryBooking --target Surgeon
onto info
onto owl export --format turtle
onto owl reason
onto owl query describe SurgeryBooking
```

### Build From Data

```bash
onto tool analyze data.csv
onto tool suggest data.csv
onto tool build data.csv
onto tool build -i data.csv
```

What this flow gives you:

- `analyze` shows the structure OntoBuilder sees in the file
- `suggest` proposes concepts and relations
- `build` creates an ontology draft
- `build -i` lets you review suggestions step by step

### AI-Assisted Workflows

First configure an LLM provider:

```bash
onto configure
```

Then you can use:

```bash
onto interview
onto infer data.csv
onto workspace data.csv
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
| `onto init` | Create a new ontology file in the current directory |
| `onto info` | Show summary information about the current ontology |
| `onto concept add/list/remove` | Manage concepts |
| `onto relation add/list/remove` | Manage relations |
| `onto save` / `onto load` | Save or load `.onto.yaml` files |
| `onto export` | Export to `yaml`, `json`, `prompt`, `jsonld`, `schema-card`, `owl`, or `turtle` |
| `onto owl export` | Export OWL as RDF/XML or Turtle |
| `onto owl reason` | Run inference and consistency checks |
| `onto owl query` | Query classes, instances, relations, descriptions, validation, or paths |
| `onto tool analyze` | Inspect a data file |
| `onto tool suggest` | Generate ontology suggestions from data |
| `onto tool build` | Build an ontology from data |
| `onto suggest` | Suggest likely next steps for the current ontology |
| `onto learn` | Show glossary-style explanations of ontology terms |
| `onto domains list/apply` | List and apply built-in domain templates |
| `onto configure` | Configure an LLM provider |
| `onto interview` | Build an ontology through an AI-assisted interview |
| `onto infer` | Infer an ontology draft from a data file |
| `onto chat` | Ask questions about the current ontology |
| `onto workspace` | Open a live AI-assisted ontology workspace |

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
onto tool build -i examples/hospital_surgery_bookings.csv
```

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE)
