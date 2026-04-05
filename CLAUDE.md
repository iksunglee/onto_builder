# OntoBuilder — Claude Code Integration

OntoBuilder is a beginner-friendly ontology builder. It helps users create structured knowledge representations with concepts, properties, relations, and instances.

## MCP Tools Available

When the MCP server is registered, you have direct access to these tools:

- `onto_init(name, description)` — Create a new ontology
- `onto_show()` — Display current ontology state and tree
- `onto_add_concept(name, description, parent)` — Add a concept/class
- `onto_add_property(concept_name, property_name, data_type, required)` — Add property to concept
- `onto_add_relation(name, source, target, cardinality)` — Add relation between concepts
- `onto_add_instance(name, concept, properties)` — Add instance of a concept
- `onto_remove_concept(name)` / `onto_remove_relation(name)` — Remove elements
- `onto_export(format)` — Export: yaml, json, owl, turtle, jsonld, prompt, schema-card
- `onto_reason()` — Run OWL inference and consistency checks
- `onto_suggest()` — Get AI-suggested next actions
- `onto_query(query_type, name, target)` — Query: classes, instances, relations, describe, path
- `onto_learn(term)` — Look up ontology terminology

## CLI Commands

Both `ontobuilder` and `onto` work as the CLI command:

```bash
ontobuilder init <name>           # Create ontology
ontobuilder info                  # Show summary
ontobuilder configure             # Set up LLM provider (OpenAI, Anthropic, Ollama, custom)
ontobuilder interview             # AI-guided ontology builder
ontobuilder infer <file>          # Infer ontology from data (CSV, JSON)
ontobuilder infer <file> --local  # Local inference (no API key needed)
ontobuilder workspace [file]      # Interactive workspace with chat
ontobuilder chat                  # Chat about your ontology
ontobuilder export -f <format>    # Export (yaml/json/owl/turtle/jsonld/prompt/schema-card)
ontobuilder concept add/list/remove
ontobuilder relation add/list/remove
ontobuilder owl export/reason/query
ontobuilder suggest               # Get next-step suggestions
ontobuilder learn <term>          # Ontology glossary
```

## Python API

```python
from ontobuilder import Ontology

onto = Ontology("MyDomain", description="...")
onto.add_concept("Animal", description="A living creature")
onto.add_concept("Dog", description="A domestic animal", parent="Animal")
onto.add_property("Animal", "name", data_type="string", required=True)
onto.add_relation("owns", source="Person", target="Animal")
```

## Ontology file

The working file is `ontology.onto.yaml` in the project root. All tools read/write this file.

## LLM Configuration

Run `ontobuilder configure` to set up the AI provider. Supports:
- **OpenAI** (gpt-4o-mini, gpt-4o)
- **Anthropic** (Claude Sonnet, Haiku, Opus) — requires `pip install ontobuilder[llm]`
- **Local models** (Ollama, LM Studio) — free, no API key
- **Custom** OpenAI-compatible endpoints

## When helping users build ontologies

1. Start with `onto_show()` to see current state
2. Ask what domain they want to model
3. Suggest top-level concepts first, then build hierarchy
4. Add properties that capture key attributes
5. Add relations to connect concepts
6. Use `onto_reason()` to check consistency
7. Export when ready
