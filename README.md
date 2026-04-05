# OntoBuilder

**Build, explore, and export ontologies from data — no PhD required.**

OntoBuilder is a Python toolkit that turns raw data (CSV, JSON) into formal ontologies with concepts, relations, properties, and OWL/RDF exports. It comes with a CLI, a web UI, LLM-powered assistance, and a beginner-friendly glossary.

---

## Features

- **Data → Ontology pipeline** — analyze CSV/JSON files, get concept and relation suggestions, build ontologies automatically or interactively
- **Rich CLI** — manage concepts, properties, relations, instances, and exports from the terminal
- **OWL/RDF export** — Turtle and RDF-XML via rdflib, with built-in reasoning and consistency checks
- **RAG-friendly exports** — JSON-LD, Schema Card, and system prompt text formats
- **LLM integration** — AI-powered interview mode, natural language chat, and structure inference
- **Domain templates** — pre-built starters for healthcare, e-commerce, and more
- **Web UI** — visual ontology builder with Streamlit
- **Graph backends** — NetworkX (built-in) and Neo4j
- **Educational glossary** — learn ontology terms as you build

---

## Installation

```bash
# Core (CLI + OWL export + reasoning)
pip install ontobuilder

# With AI features
pip install ontobuilder[llm]

# With web UI
pip install ontobuilder[web]

# Everything
pip install ontobuilder[all]
```

For development:

```bash
git clone https://github.com/iksun/ontobuilder.git
cd ontobuilder
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

# Export to OWL
onto owl export --format turtle

# Run consistency checks
onto owl reason

# Query the ontology
onto owl query describe SurgeryBooking
onto owl query path SurgeryBooking --target Hospital
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

### Web UI

```bash
pip install ontobuilder[web]
streamlit run streamlit_app.py
```

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

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

---

## License

[MIT](LICENSE)
