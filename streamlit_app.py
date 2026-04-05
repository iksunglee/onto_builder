"""OntoBuilder - Visual Ontology Builder (Streamlit UI)."""

import csv
import io
import json
import os
import streamlit as st
import yaml

from ontobuilder.core.ontology import Ontology
from ontobuilder.core.validation import ValidationError, VALID_DATA_TYPES
from ontobuilder.chat.checker import OntologyChat
from ontobuilder.domains.registry import list_builders, get_builder
from ontobuilder.education.glossary import GLOSSARY

# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------


def get_onto() -> Ontology:
    if "onto" not in st.session_state:
        st.session_state.onto = Ontology("My Ontology")
    return st.session_state.onto


def set_onto(onto: Ontology) -> None:
    st.session_state.onto = onto


def infer_next_actions(onto: Ontology, limit: int = 5) -> tuple[list[str], list[str]]:
    """Infer likely next user actions and current consistency issues."""
    checker = OntologyChat(onto)
    suggestions = checker.infer_user_intent(limit=limit)
    issues = checker.reasoner.check_consistency()
    return suggestions, issues


def flash(msg: str, level: str = "success") -> None:
    """Queue a one-time toast message."""
    st.session_state["_flash"] = (msg, level)


def show_flash() -> None:
    item = st.session_state.pop("_flash", None)
    if item:
        msg, level = item
        getattr(st, level, st.info)(msg)


# ---------------------------------------------------------------------------
# Graph visualisation (using built-in st.graphviz_chart via DOT language)
# ---------------------------------------------------------------------------


def _escape_dot(s: str) -> str:
    return s.replace('"', '\\"')


def render_graph(onto: Ontology) -> str:
    """Build a Graphviz DOT string for the ontology."""
    lines = [
        "digraph ontology {",
        "  rankdir=TB;",
        '  node [shape=box, style="rounded,filled", fillcolor="#e8f4fd", '
        'fontname="Segoe UI", fontsize=11];',
        '  edge [fontname="Segoe UI", fontsize=9];',
    ]

    for c in onto.concepts.values():
        label_parts = [f"<<b>{_escape_dot(c.name)}</b>"]
        if c.description:
            label_parts.append(f"<br/><font point-size='9'>{_escape_dot(c.description)}</font>")
        if c.properties:
            props = "<br/>".join(
                f"<font point-size='9'>  {p.name}: {p.data_type}{'*' if p.required else ''}</font>"
                for p in c.properties
            )
            label_parts.append(f"<br/>{props}")
        label_parts.append(">")
        label = "".join(label_parts)
        lines.append(f'  "{_escape_dot(c.name)}" [label={label}];')

    # is-a edges (blue, dashed)
    for c in onto.concepts.values():
        if c.parent:
            lines.append(
                f'  "{_escape_dot(c.parent)}" -> "{_escape_dot(c.name)}" '
                f'[label="is-a", style=dashed, color="#4a90d9"];'
            )

    # relation edges (green, solid)
    for r in onto.relations.values():
        lines.append(
            f'  "{_escape_dot(r.source)}" -> "{_escape_dot(r.target)}" '
            f'[label="{_escape_dot(r.name)}", color="#2ecc71", fontcolor="#27ae60"];'
        )

    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CSV analysis helpers
# ---------------------------------------------------------------------------


def analyze_csv(file_bytes: bytes) -> dict:
    """Analyze CSV columns: types, unique counts, sample values, and relationships."""
    text = file_bytes.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return {"columns": [], "rows": [], "analysis": {}, "relationships": []}

    columns = list(rows[0].keys())
    analysis = {}
    for col in columns:
        values = [r[col] for r in rows if r.get(col)]
        unique = set(values)
        # Guess type
        dtype = "string"
        if values:
            sample = [v for v in values if v.strip()][:50]
            if all(_is_int(v) for v in sample if v):
                dtype = "int"
            elif all(_is_float(v) for v in sample if v):
                dtype = "float"
            elif all(v.lower() in ("true", "false", "yes", "no", "0", "1") for v in sample if v):
                dtype = "bool"
        analysis[col] = {
            "dtype": dtype,
            "unique_count": len(unique),
            "total": len(values),
            "sample_values": list(unique)[:5],
            "nulls": sum(1 for r in rows if not r.get(col, "").strip()),
        }

    # Detect likely relationships (foreign-key patterns)
    relationships = []
    id_cols = [c for c in columns if c.lower().endswith("_id") or c.lower() == "id"]
    for col in columns:
        if col.lower().endswith("_id") and col.lower() != "id":
            # e.g. "customer_id" likely references a "Customer" entity
            ref_entity = col.replace("_id", "").replace("_", " ").title().replace(" ", "")
            relationships.append(
                {
                    "column": col,
                    "type": "foreign_key",
                    "references": ref_entity,
                    "description": f"{col} likely references {ref_entity}",
                }
            )
    # Detect categorical columns (low cardinality = likely enum/type)
    for col, info in analysis.items():
        if col not in id_cols and info["dtype"] == "string":
            ratio = info["unique_count"] / max(info["total"], 1)
            if 1 < info["unique_count"] <= 10 and ratio < 0.3:
                relationships.append(
                    {
                        "column": col,
                        "type": "categorical",
                        "references": None,
                        "description": f"{col} is categorical ({info['unique_count']} unique values)",
                    }
                )
    # Detect one-to-many (column with ID + another column with repeating values)
    if "id" in [c.lower() for c in columns]:
        for col, info in analysis.items():
            if (
                col.lower() != "id"
                and info["dtype"] == "string"
                and info["unique_count"] < info["total"] * 0.5
            ):
                if info["unique_count"] > 1:
                    relationships.append(
                        {
                            "column": col,
                            "type": "one_to_many",
                            "references": None,
                            "description": f"Multiple rows share the same {col} (one-to-many pattern)",
                        }
                    )

    return {
        "columns": columns,
        "rows": rows,
        "analysis": analysis,
        "relationships": relationships,
    }


def _is_int(v: str) -> bool:
    try:
        int(v.strip())
        return True
    except (ValueError, AttributeError):
        return False


def _is_float(v: str) -> bool:
    try:
        float(v.strip())
        return True
    except (ValueError, AttributeError):
        return False


def csv_to_markdown_table(rows: list[dict], max_rows: int = 20) -> str:
    """Convert CSV rows to a markdown table string for LLM."""
    if not rows:
        return "(empty)"
    cols = list(rows[0].keys())
    lines = [" | ".join(cols), " | ".join("---" for _ in cols)]
    for row in rows[:max_rows]:
        lines.append(" | ".join(row.get(c, "") for c in cols))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="OntoBuilder", page_icon="🧠", layout="wide")
st.title("OntoBuilder")
st.caption("A visual ontology builder -- no coding required")

show_flash()

onto = get_onto()

# ---------------------------------------------------------------------------
# Sidebar: project-level actions
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Project")

    # -- Rename --
    new_name = st.text_input("Ontology name", value=onto.name, key="onto_name_input")
    if new_name != onto.name:
        onto.name = new_name

    new_desc = st.text_input("Description", value=onto.description, key="onto_desc_input")
    if new_desc != onto.description:
        onto.description = new_desc

    st.divider()

    # -- Domain templates --
    st.subheader("Quick start from template")
    builders = list_builders()
    template_names = ["(none)"] + [b.name for b in builders]
    choice = st.selectbox("Domain template", template_names, key="tmpl")
    if st.button("Apply template") and choice != "(none)":
        builder = get_builder(choice)
        if builder:
            set_onto(builder.build_template())
            flash(f"Applied '{choice}' template!")
            st.rerun()

    st.divider()

    # -- Import / Export --
    st.subheader("Import / Export")

    uploaded = st.file_uploader("Import .onto.yaml or .json", type=["yaml", "yml", "json"])
    if uploaded is not None:
        try:
            raw = uploaded.read().decode("utf-8")
            if uploaded.name.endswith(".json"):
                data = json.loads(raw)
            else:
                data = yaml.safe_load(raw)
            set_onto(Ontology.from_dict(data))
            flash(f"Imported '{uploaded.name}'!")
            st.rerun()
        except Exception as e:
            st.error(f"Import failed: {e}")

    col_y, col_j = st.columns(2)
    with col_y:
        yaml_str = yaml.dump(onto.to_dict(), default_flow_style=False, sort_keys=False)
        st.download_button(
            "Download YAML", yaml_str, file_name="ontology.onto.yaml", mime="text/yaml"
        )
    with col_j:
        json_str = json.dumps(onto.to_dict(), indent=2)
        st.download_button(
            "Download JSON", json_str, file_name="ontology.json", mime="application/json"
        )

    st.divider()

    with st.expander("🤖 Export for LLM / RAG", expanded=False):
        st.caption(
            "Export your ontology in formats optimized for LLM consumption and RAG pipelines."
        )
        from ontobuilder.serialization.prompt_io import export_prompt
        from ontobuilder.serialization.jsonld_io import export_jsonld
        from ontobuilder.serialization.schemacard_io import export_schema_card

        st.download_button(
            "📄 System Prompt (.txt)",
            data=export_prompt(onto),
            file_name="ontology.prompt.txt",
            mime="text/plain",
            use_container_width=True,
        )
        st.download_button(
            "🔗 JSON-LD (.jsonld)",
            data=export_jsonld(onto),
            file_name="ontology.jsonld",
            mime="application/ld+json",
            use_container_width=True,
        )
        st.download_button(
            "📋 Schema Card (.json)",
            data=export_schema_card(onto),
            file_name="ontology.schema-card.json",
            mime="application/json",
            use_container_width=True,
        )

    st.divider()

    # -- Stats --
    st.subheader("Stats")
    st.metric("Concepts", len(onto.concepts))
    st.metric("Relations", len(onto.relations))
    st.metric("Instances", len(onto.instances))

# ---------------------------------------------------------------------------
# Main area: tabs
# ---------------------------------------------------------------------------

(
    tab_upload,
    tab_graph,
    tab_next,
    tab_chat,
    tab_ai,
    tab_concepts,
    tab_relations,
    tab_instances,
    tab_learn,
) = st.tabs(
    [
        "CSV Upload",
        "Graph",
        "Next Actions",
        "Chat",
        "AI Assistant",
        "Concepts",
        "Relations",
        "Instances",
        "Learn",
    ]
)

# ===================== CSV UPLOAD TAB =====================
with tab_upload:
    st.subheader("Build Ontology from CSV Data")
    st.caption(
        "Upload a CSV file and the AI will analyze column relationships and build an ontology."
    )

    # --- LLM settings (shared) ---
    with st.expander(
        "OpenAI Settings",
        expanded=not bool(
            os.environ.get("ONTOBUILDER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        ),
    ):
        csv_api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=os.environ.get("ONTOBUILDER_API_KEY", os.environ.get("OPENAI_API_KEY", "")),
            help="Your OpenAI API key",
            key="csv_api_key",
        )
        csv_model = st.text_input(
            "Model",
            value=os.environ.get("ONTOBUILDER_LLM_MODEL", "gpt-4o-mini"),
            help="OpenAI model to use (e.g. gpt-4o-mini, gpt-4o)",
            key="csv_model",
        )
        if csv_api_key:
            os.environ["ONTOBUILDER_API_KEY"] = csv_api_key
            os.environ["OPENAI_API_KEY"] = csv_api_key
        if csv_model:
            os.environ["ONTOBUILDER_LLM_MODEL"] = csv_model

    csv_file = st.file_uploader("Upload CSV file", type=["csv"], key="csv_upload")

    if csv_file is not None:
        file_bytes = csv_file.read()
        csv_file.seek(0)  # Reset for re-reads

        # Analyze the CSV
        if (
            "csv_analysis" not in st.session_state
            or st.session_state.get("_csv_name") != csv_file.name
        ):
            st.session_state.csv_analysis = analyze_csv(file_bytes)
            st.session_state._csv_name = csv_file.name

        analysis = st.session_state.csv_analysis

        # --- Show data preview ---
        st.markdown("### Data Preview")
        import pandas as pd

        df = pd.DataFrame(analysis["rows"])
        st.dataframe(df.head(20), use_container_width=True)

        # --- Show column analysis ---
        st.markdown("### Column Analysis")
        col_data = []
        for col, info in analysis["analysis"].items():
            col_data.append(
                {
                    "Column": col,
                    "Type": info["dtype"],
                    "Unique": info["unique_count"],
                    "Total": info["total"],
                    "Nulls": info["nulls"],
                    "Sample Values": ", ".join(str(v) for v in info["sample_values"][:3]),
                }
            )
        st.dataframe(pd.DataFrame(col_data), use_container_width=True, hide_index=True)

        # --- Show detected relationships ---
        if analysis["relationships"]:
            st.markdown("### Detected Relationships")
            for rel in analysis["relationships"]:
                icon = {"foreign_key": "🔗", "categorical": "📊", "one_to_many": "↔️"}.get(
                    rel["type"], "•"
                )
                st.markdown(f"- {icon} **{rel['column']}**: {rel['description']}")

        # --- Build ontology button ---
        st.markdown("---")
        has_key = bool(os.environ.get("ONTOBUILDER_API_KEY") or os.environ.get("OPENAI_API_KEY"))

        if not has_key:
            st.warning("Enter your OpenAI API key above to build an ontology from this data.")
        else:
            if st.button("Build Ontology from CSV", type="primary", key="build_onto_btn"):
                with st.spinner("AI is analyzing your data and building an ontology..."):
                    try:
                        from ontobuilder.llm.client import chat
                        from ontobuilder.llm.schemas import OntologySuggestion

                        # Build a rich prompt with the analysis
                        table = csv_to_markdown_table(analysis["rows"])
                        rel_desc = ""
                        if analysis["relationships"]:
                            rel_desc = "\n\nDetected patterns:\n" + "\n".join(
                                f"- {r['description']}" for r in analysis["relationships"]
                            )

                        col_types = "\n".join(
                            f"- {col}: {info['dtype']} ({info['unique_count']} unique values)"
                            for col, info in analysis["analysis"].items()
                        )

                        prompt_text = (
                            f"Analyze this CSV data and build an ontology that captures the "
                            f"logical structure and relationships between columns.\n\n"
                            f"Column types:\n{col_types}\n{rel_desc}\n\n"
                            f"Data sample:\n{table}\n\n"
                            f"Based on the columns, values, and patterns:\n"
                            f"1. Identify main concepts (entities/classes) — columns often represent "
                            f"properties of entities, group related columns into concepts\n"
                            f"2. Determine properties for each concept (from column names and data types)\n"
                            f"3. Identify relationships between concepts (foreign keys, shared values, "
                            f"hierarchical patterns)\n"
                            f"4. Organize concepts in a hierarchy if appropriate\n"
                            f"5. Set correct cardinality for relationships (one-to-one, one-to-many, "
                            f"many-to-many)\n\n"
                            f"Be thorough — capture all meaningful relationships in the data."
                        )

                        messages = [
                            {
                                "role": "system",
                                "content": (
                                    "You are an ontology design expert. You analyze tabular data and "
                                    "design OWL-compatible ontologies that capture the logical structure, "
                                    "entity types, properties, and relationships in the data."
                                ),
                            },
                            {"role": "user", "content": prompt_text},
                        ]

                        suggestion: OntologySuggestion = chat(
                            messages, response_model=OntologySuggestion
                        )

                        # Build the ontology
                        new_onto = Ontology(suggestion.name, description=suggestion.description)
                        added: set[str] = set()
                        remaining = list(suggestion.concepts)
                        max_passes = len(remaining) + 1
                        while remaining and max_passes > 0:
                            max_passes -= 1
                            still_remaining = []
                            for c in remaining:
                                if c.parent and c.parent not in added:
                                    still_remaining.append(c)
                                else:
                                    parent = c.parent if c.parent and c.parent in added else None
                                    new_onto.add_concept(
                                        c.name, description=c.description, parent=parent
                                    )
                                    for p in c.properties:
                                        dt = (
                                            p.data_type
                                            if p.data_type
                                            in {"string", "int", "float", "bool", "date"}
                                            else "string"
                                        )
                                        try:
                                            new_onto.add_property(
                                                c.name, p.name, data_type=dt, required=p.required
                                            )
                                        except ValidationError:
                                            pass
                                    added.add(c.name)
                            remaining = still_remaining

                        for r in suggestion.relations:
                            if r.source in added and r.target in added:
                                try:
                                    new_onto.add_relation(
                                        r.name,
                                        source=r.source,
                                        target=r.target,
                                        cardinality=r.cardinality,
                                    )
                                except ValidationError:
                                    pass

                        set_onto(new_onto)
                        onto = new_onto
                        flash(
                            f"Built ontology '{new_onto.name}' with {len(new_onto.concepts)} concepts and {len(new_onto.relations)} relations!"
                        )
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error building ontology: {e}")

            # Show current ontology if it exists
            if onto.concepts:
                st.markdown("---")
                st.success(
                    f"Current ontology: **{onto.name}** -- {len(onto.concepts)} concepts, {len(onto.relations)} relations"
                )
                st.caption(
                    "Go to the **Graph** tab to visualize, or **Chat** tab to ask questions."
                )


# ===================== GRAPH TAB =====================
with tab_graph:
    if onto.concepts:
        dot = render_graph(onto)
        st.graphviz_chart(dot, use_container_width=True)
        st.caption("Blue dashed = is-a hierarchy | Green = relations | * = required property")
    else:
        st.info(
            "Add some concepts to see the graph! Use the Concepts tab or apply a domain template from the sidebar."
        )


# ===================== NEXT ACTIONS TAB =====================
with tab_next:
    st.subheader("What should I do next?")
    st.caption(
        "These suggestions are inferred from your ontology structure and consistency checks."
    )

    if not onto.concepts:
        st.info("Start by adding a few concepts, then return here for guided next steps.")
    else:
        limit = st.slider(
            "Number of suggestions", min_value=3, max_value=10, value=5, key="next_limit"
        )
        suggestions, issues = infer_next_actions(onto, limit=limit)

        st.markdown("### Suggested next steps")
        for i, suggestion in enumerate(suggestions, start=1):
            st.markdown(f"{i}. {suggestion}")

        with st.expander("Consistency status", expanded=bool(issues)):
            if issues:
                st.error(f"{len(issues)} issue(s) detected")
                for issue in issues:
                    st.markdown(f"- {issue}")
            else:
                st.success("No consistency issues detected.")

        with st.expander("Hierarchy preview"):
            st.code(onto.print_tree(), language="text")

# ===================== CHAT TAB =====================
with tab_chat:
    st.subheader("Chat with your Ontology")
    st.caption(
        "Ask questions about your ontology and data -- the AI sees both the ontology structure and original CSV analysis."
    )

    if not onto.concepts:
        st.info(
            "Build an ontology first (use the **CSV Upload** tab or **AI Assistant** tab), then come back here to chat."
        )
    else:
        has_key = bool(os.environ.get("ONTOBUILDER_API_KEY") or os.environ.get("OPENAI_API_KEY"))
        if not has_key:
            st.warning(
                "Enter your OpenAI API key in the **CSV Upload** tab or **AI Assistant** tab to use chat."
            )
        else:
            # Initialize chat state
            if "chat_messages" not in st.session_state:
                st.session_state.chat_messages = []

            # Build full context: ontology + CSV analysis + reasoning
            def _build_chat_context() -> str:
                """Build rich context combining ontology structure and CSV data analysis."""
                from ontobuilder.owl.reasoning import OWLReasoner

                reasoner = OWLReasoner(onto)

                sections = []

                # -- Ontology structure --
                sections.append(f"# Ontology: {onto.name}")
                if onto.description:
                    sections.append(f"Description: {onto.description}")
                sections.append("")

                sections.append("## Classes (Concepts)")
                for name, concept in onto.concepts.items():
                    parent_info = (
                        f" (subClassOf: {concept.parent})" if concept.parent else " [root]"
                    )
                    sections.append(f"- **{name}**{parent_info}")
                    if concept.description:
                        sections.append(f"  Description: {concept.description}")
                    all_props = reasoner.get_all_properties(name)
                    if all_props:
                        for pname, info in all_props.items():
                            inh = " [inherited]" if info["inherited"] else ""
                            req = " [required]" if info["required"] else ""
                            sections.append(f"  Property: {pname} ({info['data_type']}{req}{inh})")
                sections.append("")

                sections.append("## Relations (Object Properties)")
                if onto.relations:
                    for name, rel in onto.relations.items():
                        sections.append(
                            f"- {name}: {rel.source} -> {rel.target} ({rel.cardinality})"
                        )
                else:
                    sections.append("(none)")
                sections.append("")

                if onto.instances:
                    sections.append("## Instances (Individuals)")
                    for name, inst in onto.instances.items():
                        types = reasoner.classify_instance(name)
                        sections.append(f"- {name} (type: {', '.join(types)})")
                        for k, v in inst.properties.items():
                            sections.append(f"  {k}: {v}")
                    sections.append("")

                # -- Consistency check --
                issues = reasoner.check_consistency()
                if issues:
                    sections.append("## Consistency Issues Detected")
                    for issue in issues:
                        sections.append(f"- {issue}")
                    sections.append("")

                # -- Hierarchy --
                sections.append("## Class Hierarchy")
                sections.append("```")
                sections.append(onto.print_tree())
                sections.append("```")
                sections.append("")

                # -- CSV data analysis (if available) --
                csv_analysis = st.session_state.get("csv_analysis")
                if csv_analysis:
                    sections.append("## Source CSV Data Analysis")
                    sections.append(
                        f"The ontology was built from a CSV file with {len(csv_analysis['rows'])} rows and {len(csv_analysis['columns'])} columns."
                    )
                    sections.append("")

                    sections.append("### Column Details")
                    for col, info in csv_analysis["analysis"].items():
                        sections.append(
                            f"- **{col}**: type={info['dtype']}, "
                            f"{info['unique_count']} unique values out of {info['total']} total, "
                            f"{info['nulls']} nulls, "
                            f"samples: {info['sample_values'][:5]}"
                        )
                    sections.append("")

                    if csv_analysis["relationships"]:
                        sections.append("### Detected Data Relationships")
                        for rel in csv_analysis["relationships"]:
                            sections.append(f"- [{rel['type']}] {rel['description']}")
                        sections.append("")

                    # Include sample rows
                    sections.append("### Sample Data (first 10 rows)")
                    sections.append(csv_to_markdown_table(csv_analysis["rows"], max_rows=10))
                    sections.append("")

                return "\n".join(sections)

            # Rebuild context when ontology changes
            _ctx_key = f"{id(onto)}_{len(onto.concepts)}_{len(onto.relations)}"
            if st.session_state.get("_chat_ctx_key") != _ctx_key:
                st.session_state._chat_ctx_key = _ctx_key
                st.session_state._chat_context = _build_chat_context()
                st.session_state._chat_history = []  # Reset LLM history on ontology change
                # Reset welcome message
                st.session_state.chat_messages = [
                    {
                        "role": "assistant",
                        "content": (
                            f"I'm connected to your **{onto.name}** ontology "
                            f"({len(onto.concepts)} concepts, {len(onto.relations)} relations)"
                            + (
                                f" built from your CSV data ({len(st.session_state.get('csv_analysis', {}).get('rows', []))} rows)."
                                if st.session_state.get("csv_analysis")
                                else "."
                            )
                            + "\n\nI can see both the ontology structure and the original data analysis. Ask me anything:\n"
                            f"- *'Why did you create the X concept?'*\n"
                            f"- *'What relationships exist between X and Y?'*\n"
                            f"- *'Is there anything missing?'*\n"
                            f"- *'Explain the hierarchy'*\n"
                            f"- *'What data patterns led to this structure?'*"
                        ),
                    }
                ]

            # Display chat history
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # Chat input
            if user_input := st.chat_input("Ask about your ontology and data..."):
                st.session_state.chat_messages.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            from ontobuilder.llm.client import chat as llm_chat

                            # Build messages with full context
                            if not st.session_state.get("_chat_history"):
                                system_msg = (
                                    "You are an expert ontology analyst. The user has built an ontology "
                                    "from their CSV data. You have access to BOTH the full ontology structure "
                                    "AND the original data analysis below.\n\n"
                                    "When answering:\n"
                                    "- Reference specific classes, properties, and relations by name\n"
                                    "- Explain WHY certain modeling decisions make sense given the data\n"
                                    "- Point out data patterns that support or contradict the ontology structure\n"
                                    "- Suggest improvements based on what you see in both the ontology and data\n"
                                    "- Check for consistency issues, missing relationships, or redundancies\n"
                                    "- If asked about the data, reference actual column statistics and sample values\n\n"
                                    "Be specific and cite concrete evidence from the data and ontology.\n\n"
                                    "---\n\n" + st.session_state._chat_context
                                )
                                st.session_state._chat_history = [
                                    {"role": "system", "content": system_msg}
                                ]

                            st.session_state._chat_history.append(
                                {"role": "user", "content": user_input}
                            )
                            answer = llm_chat(st.session_state._chat_history)
                            st.session_state._chat_history.append(
                                {"role": "assistant", "content": answer}
                            )

                            st.markdown(answer)
                            st.session_state.chat_messages.append(
                                {"role": "assistant", "content": answer}
                            )
                        except Exception as e:
                            err_msg = f"Error: {e}"
                            st.error(err_msg)
                            st.session_state.chat_messages.append(
                                {"role": "assistant", "content": err_msg}
                            )

            # Clear chat button
            if st.session_state.chat_messages:
                if st.button("Clear chat history", key="clear_chat"):
                    st.session_state.chat_messages = []
                    st.session_state._chat_history = []
                    st.session_state._chat_ctx_key = None
                    st.rerun()


# ===================== AI ASSISTANT TAB =====================
with tab_ai:
    st.subheader("AI-Powered Ontology Builder")

    # --- LLM availability check ---
    def _check_llm_deps() -> str | None:
        """Return an error message if LLM deps are missing, else None."""
        try:
            import litellm  # noqa: F401
            import instructor  # noqa: F401
            import pydantic  # noqa: F401

            return None
        except ImportError:
            return "LLM dependencies not installed. Run:\n\n```\npip install ontobuilder[llm]\n```"

    llm_err = _check_llm_deps()
    if llm_err:
        st.warning(llm_err)
    else:
        # --- API key config ---
        with st.expander(
            "LLM Settings",
            expanded=not bool(
                os.environ.get("ONTOBUILDER_API_KEY") or os.environ.get("OPENAI_API_KEY")
            ),
        ):
            api_key_input = st.text_input(
                "API Key",
                type="password",
                value=os.environ.get("ONTOBUILDER_API_KEY", os.environ.get("OPENAI_API_KEY", "")),
                help="Your OpenAI / LiteLLM-compatible API key",
                key="llm_api_key",
            )
            model_input = st.text_input(
                "Model",
                value=os.environ.get("ONTOBUILDER_LLM_MODEL", "gpt-4o-mini"),
                help="Any model supported by LiteLLM (e.g. gpt-4o, claude-sonnet-4-20250514, etc.)",
                key="llm_model",
            )
            if api_key_input:
                os.environ["ONTOBUILDER_API_KEY"] = api_key_input
                os.environ["OPENAI_API_KEY"] = api_key_input
            if model_input:
                os.environ["ONTOBUILDER_LLM_MODEL"] = model_input

        has_key = bool(os.environ.get("ONTOBUILDER_API_KEY") or os.environ.get("OPENAI_API_KEY"))

        if not has_key:
            st.info("Enter your API key above to use AI features.")
        else:
            has_existing = bool(onto.concepts)

            # --- Initialize interview state ---
            if "iv" not in st.session_state:
                st.session_state.iv = {
                    "step": "idle",  # idle | scoping | answering | reviewing | done
                    "questions": [],  # list of question strings
                    "answers": [],  # list of user answers
                    "suggestion": None,  # OntologySuggestion object
                    "selections": {},  # concept/relation name -> bool
                    "error": None,
                }
            iv = st.session_state.iv

            # Show errors
            if iv["error"]:
                st.error(iv["error"])
                if st.button("Dismiss error"):
                    iv["error"] = None
                    st.rerun()

            # ---- Mode description ----
            if has_existing:
                st.markdown(
                    "Your ontology already has **{} concepts** and **{} relations**. "
                    "The AI will analyze what you have and suggest additions.".format(
                        len(onto.concepts), len(onto.relations)
                    )
                )
            else:
                st.markdown(
                    "Your ontology is empty. The AI will interview you about your "
                    "domain and build an ontology from scratch."
                )

            # ========== STEP: IDLE ==========
            if iv["step"] == "idle":
                if has_existing:
                    st.markdown("---")
                    st.markdown("**Describe what you'd like to add or improve:**")
                    enhance_request = st.text_area(
                        "Your request",
                        placeholder="e.g., Add concepts for shipping and delivery tracking, "
                        "or expand the product hierarchy with more categories...",
                        key="enhance_request",
                        label_visibility="collapsed",
                    )
                    if st.button("Get AI suggestions", type="primary"):
                        if not enhance_request.strip():
                            st.warning("Please describe what you'd like to add.")
                        else:
                            iv["step"] = "enhancing"
                            iv["enhance_request"] = enhance_request.strip()
                            st.rerun()
                else:
                    if st.button("Start AI Interview", type="primary"):
                        iv["step"] = "scoping"
                        st.rerun()

            # ========== STEP: SCOPING (fresh interview) ==========
            elif iv["step"] == "scoping":
                with st.spinner("AI is preparing questions about your domain..."):
                    try:
                        from ontobuilder.llm.client import chat
                        from ontobuilder.llm.schemas import InterviewQuestions
                        from ontobuilder.llm.prompts import interview_scoping_prompt

                        result = chat(
                            interview_scoping_prompt(), response_model=InterviewQuestions
                        )
                        iv["questions"] = [q.question for q in result.questions]
                        iv["answers"] = [""] * len(iv["questions"])
                        iv["step"] = "answering"
                        st.rerun()
                    except Exception as e:
                        iv["error"] = f"LLM error: {e}"
                        iv["step"] = "idle"
                        st.rerun()

            # ========== STEP: ANSWERING (user answers scoping questions) ==========
            elif iv["step"] == "answering":
                st.markdown("### Answer these questions about your domain")
                st.caption("The AI will use your answers to design an ontology.")

                with st.form("interview_answers_form"):
                    answers = []
                    for i, q in enumerate(iv["questions"]):
                        st.markdown(f"**Q{i + 1}: {q}**")
                        ans = st.text_area(
                            f"Answer {i + 1}",
                            key=f"iv_ans_{i}",
                            label_visibility="collapsed",
                            height=80,
                        )
                        answers.append(ans)

                    col_submit, col_cancel = st.columns([1, 1])
                    with col_submit:
                        submitted = st.form_submit_button("Generate ontology", type="primary")
                    with col_cancel:
                        cancelled = st.form_submit_button("Cancel")

                if cancelled:
                    iv["step"] = "idle"
                    iv["questions"] = []
                    iv["answers"] = []
                    st.rerun()
                elif submitted:
                    if all(a.strip() for a in answers):
                        iv["answers"] = answers
                        iv["step"] = "generating"
                        st.rerun()
                    else:
                        st.warning("Please answer all questions.")

            # ========== STEP: GENERATING (fresh interview -> LLM call) ==========
            elif iv["step"] == "generating":
                with st.spinner("AI is designing your ontology..."):
                    try:
                        from ontobuilder.llm.client import chat
                        from ontobuilder.llm.schemas import OntologySuggestion
                        from ontobuilder.llm.prompts import (
                            interview_concepts_prompt,
                            interview_relations_prompt,
                        )

                        context = "\n\n".join(
                            f"Q: {q}\nA: {a}" for q, a in zip(iv["questions"], iv["answers"])
                        )

                        # Get concepts
                        suggestion = chat(
                            interview_concepts_prompt(context),
                            response_model=OntologySuggestion,
                        )

                        # Get relations
                        concept_names = [c.name for c in suggestion.concepts]
                        rel_result = chat(
                            interview_relations_prompt(context, concept_names),
                            response_model=OntologySuggestion,
                        )
                        # Merge relations into suggestion
                        suggestion.relations = [
                            r
                            for r in rel_result.relations
                            if r.source in concept_names and r.target in concept_names
                        ]

                        iv["suggestion"] = suggestion
                        iv["selections"] = {}
                        for c in suggestion.concepts:
                            iv["selections"][f"concept:{c.name}"] = True
                        for r in suggestion.relations:
                            iv["selections"][f"relation:{r.name}"] = True
                        iv["step"] = "reviewing"
                        st.rerun()
                    except Exception as e:
                        iv["error"] = f"LLM error: {e}"
                        iv["step"] = "idle"
                        st.rerun()

            # ========== STEP: ENHANCING (existing ontology -> LLM call) ==========
            elif iv["step"] == "enhancing":
                with st.spinner("AI is analyzing your ontology and preparing suggestions..."):
                    try:
                        from ontobuilder.llm.client import chat
                        from ontobuilder.llm.schemas import OntologySuggestion
                        from ontobuilder.llm.prompts import enhance_existing_prompt

                        concept_descs = []
                        for c in onto.concepts.values():
                            desc = c.name
                            if c.parent:
                                desc += f" (child of {c.parent})"
                            if c.description:
                                desc += f" - {c.description}"
                            if c.properties:
                                props = ", ".join(f"{p.name}:{p.data_type}" for p in c.properties)
                                desc += f" [{props}]"
                            concept_descs.append(desc)

                        relation_descs = [
                            f"{r.name}: {r.source} -> {r.target} ({r.cardinality})"
                            for r in onto.relations.values()
                        ]

                        suggestion = chat(
                            enhance_existing_prompt(
                                name=onto.name,
                                description=onto.description,
                                concepts=concept_descs,
                                relations=relation_descs,
                                user_request=iv.get("enhance_request", "Suggest improvements"),
                            ),
                            response_model=OntologySuggestion,
                        )

                        # Filter out concepts/relations that already exist
                        existing_concepts = set(onto.concepts.keys())
                        existing_relations = set(onto.relations.keys())
                        suggestion.concepts = [
                            c for c in suggestion.concepts if c.name not in existing_concepts
                        ]
                        suggestion.relations = [
                            r for r in suggestion.relations if r.name not in existing_relations
                        ]

                        iv["suggestion"] = suggestion
                        iv["selections"] = {}
                        for c in suggestion.concepts:
                            iv["selections"][f"concept:{c.name}"] = True
                        for r in suggestion.relations:
                            iv["selections"][f"relation:{r.name}"] = True
                        iv["step"] = "reviewing"
                        st.rerun()
                    except Exception as e:
                        iv["error"] = f"LLM error: {e}"
                        iv["step"] = "idle"
                        st.rerun()

            # ========== STEP: REVIEWING (user picks which suggestions to apply) ==========
            elif iv["step"] == "reviewing":
                suggestion = iv["suggestion"]
                if suggestion is None:
                    iv["step"] = "idle"
                    st.rerun()
                else:
                    st.markdown(f"### AI Suggestions: {suggestion.name}")
                    if suggestion.description:
                        st.caption(suggestion.description)

                    if not suggestion.concepts and not suggestion.relations:
                        st.info(
                            "The AI didn't suggest any new additions. Try a different request."
                        )
                        if st.button("Back"):
                            iv["step"] = "idle"
                            st.rerun()
                    else:
                        # Concepts
                        if suggestion.concepts:
                            st.markdown("#### Suggested Concepts")
                            st.caption("Uncheck any you don't want to add.")
                            for c in suggestion.concepts:
                                key = f"concept:{c.name}"
                                parent_str = f" (child of **{c.parent}**)" if c.parent else ""
                                props_str = ""
                                if c.properties:
                                    props_str = " -- properties: " + ", ".join(
                                        f"`{p.name}` ({p.data_type})" for p in c.properties
                                    )
                                label = f"**{c.name}**{parent_str}: {c.description}{props_str}"
                                iv["selections"][key] = st.checkbox(
                                    label, value=iv["selections"].get(key, True), key=f"sel_{key}"
                                )

                        # Relations
                        if suggestion.relations:
                            st.markdown("#### Suggested Relations")
                            for r in suggestion.relations:
                                key = f"relation:{r.name}"
                                label = f"**{r.name}**: {r.source} -> {r.target} ({r.cardinality})"
                                iv["selections"][key] = st.checkbox(
                                    label, value=iv["selections"].get(key, True), key=f"sel_{key}"
                                )

                        st.markdown("---")
                        col_apply, col_cancel2 = st.columns([1, 1])
                        with col_apply:
                            if st.button("Apply selected", type="primary"):
                                applied_c = 0
                                applied_r = 0
                                errors = []

                                # Apply concepts in parent-first order
                                selected_concepts = [
                                    c
                                    for c in suggestion.concepts
                                    if iv["selections"].get(f"concept:{c.name}", False)
                                ]
                                all_known = set(onto.concepts.keys())
                                remaining = list(selected_concepts)
                                max_passes = len(remaining) + 1
                                while remaining and max_passes > 0:
                                    max_passes -= 1
                                    still_remaining = []
                                    for c in remaining:
                                        if c.parent and c.parent not in all_known:
                                            still_remaining.append(c)
                                        else:
                                            try:
                                                parent = (
                                                    c.parent
                                                    if c.parent and c.parent in all_known
                                                    else None
                                                )
                                                onto.add_concept(
                                                    c.name,
                                                    description=c.description,
                                                    parent=parent,
                                                )
                                                for p in c.properties:
                                                    dt = (
                                                        p.data_type
                                                        if p.data_type
                                                        in {
                                                            "string",
                                                            "int",
                                                            "float",
                                                            "bool",
                                                            "date",
                                                        }
                                                        else "string"
                                                    )
                                                    try:
                                                        onto.add_property(
                                                            c.name,
                                                            p.name,
                                                            data_type=dt,
                                                            required=p.required,
                                                        )
                                                    except ValidationError:
                                                        pass
                                                all_known.add(c.name)
                                                applied_c += 1
                                            except ValidationError as e:
                                                errors.append(str(e))
                                    remaining = still_remaining

                                # Apply relations
                                for r in suggestion.relations:
                                    if iv["selections"].get(f"relation:{r.name}", False):
                                        try:
                                            onto.add_relation(
                                                r.name,
                                                source=r.source,
                                                target=r.target,
                                                cardinality=r.cardinality,
                                            )
                                            applied_r += 1
                                        except ValidationError as e:
                                            errors.append(str(e))

                                msg = f"Applied {applied_c} concepts and {applied_r} relations!"
                                if errors:
                                    msg += f" ({len(errors)} skipped due to conflicts)"
                                flash(msg)
                                iv["step"] = "done"
                                st.rerun()

                        with col_cancel2:
                            if st.button("Discard all"):
                                iv["step"] = "idle"
                                iv["suggestion"] = None
                                st.rerun()

            # ========== STEP: DONE ==========
            elif iv["step"] == "done":
                st.success("AI suggestions applied! Check the Graph tab to see your ontology.")
                if st.button("Start another round"):
                    iv["step"] = "idle"
                    iv["suggestion"] = None
                    iv["questions"] = []
                    iv["answers"] = []
                    iv["selections"] = {}
                    st.rerun()

# ===================== CONCEPTS TAB =====================
with tab_concepts:
    st.subheader("Add a concept")

    with st.form("add_concept_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            concept_name = st.text_input("Concept name *")
        with c2:
            parent_options = ["(none)"] + sorted(onto.concepts.keys())
            parent_choice = st.selectbox("Parent concept", parent_options)
        concept_desc = st.text_input("Description")

        if st.form_submit_button("Add concept"):
            if concept_name.strip():
                try:
                    parent = parent_choice if parent_choice != "(none)" else None
                    onto.add_concept(
                        concept_name.strip(),
                        description=concept_desc.strip(),
                        parent=parent,
                    )
                    flash(f"Added concept '{concept_name.strip()}'!")
                    st.rerun()
                except ValidationError as e:
                    st.error(str(e))
            else:
                st.warning("Please enter a concept name.")

    # -- Add property to concept --
    if onto.concepts:
        st.subheader("Add a property")
        with st.form("add_prop_form", clear_on_submit=True):
            p1, p2, p3, p4 = st.columns([3, 3, 2, 1])
            with p1:
                prop_concept = st.selectbox(
                    "To concept", sorted(onto.concepts.keys()), key="prop_concept"
                )
            with p2:
                prop_name = st.text_input("Property name *", key="prop_name")
            with p3:
                prop_type = st.selectbox("Type", sorted(VALID_DATA_TYPES), key="prop_type")
            with p4:
                prop_req = st.checkbox("Required", key="prop_req")

            if st.form_submit_button("Add property"):
                if prop_name.strip():
                    try:
                        onto.add_property(
                            prop_concept,
                            prop_name.strip(),
                            data_type=prop_type,
                            required=prop_req,
                        )
                        flash(f"Added property '{prop_name.strip()}' to '{prop_concept}'!")
                        st.rerun()
                    except ValidationError as e:
                        st.error(str(e))
                else:
                    st.warning("Please enter a property name.")

    # -- Existing concepts --
    if onto.concepts:
        st.subheader("Existing concepts")

        # Tree view
        with st.expander("Hierarchy (tree view)"):
            st.code(onto.print_tree(), language=None)

        # Detailed list
        for cname, concept in sorted(onto.concepts.items()):
            with st.expander(
                f"{concept.name}" + (f" (child of {concept.parent})" if concept.parent else "")
            ):
                if concept.description:
                    st.write(concept.description)
                if concept.properties:
                    st.markdown("**Properties:**")
                    for p in concept.properties:
                        req = " (required)" if p.required else ""
                        st.write(f"- `{p.name}`: {p.data_type}{req}")
                # Show children
                children = [c for c in onto.concepts.values() if c.parent == cname]
                if children:
                    st.markdown("**Children:** " + ", ".join(c.name for c in children))

                if st.button(f"Remove '{cname}'", key=f"rm_concept_{cname}"):
                    onto.remove_concept(cname)
                    flash(f"Removed concept '{cname}'.")
                    st.rerun()

# ===================== RELATIONS TAB =====================
with tab_relations:
    concept_names = sorted(onto.concepts.keys())

    if len(concept_names) >= 2:
        st.subheader("Add a relation")
        with st.form("add_rel_form", clear_on_submit=True):
            r1, r2, r3, r4 = st.columns([3, 2, 2, 2])
            with r1:
                rel_name = st.text_input("Relation name *")
            with r2:
                rel_source = st.selectbox("From (source)", concept_names, key="rel_src")
            with r3:
                rel_target = st.selectbox("To (target)", concept_names, key="rel_tgt")
            with r4:
                rel_card = st.selectbox(
                    "Cardinality",
                    ["many-to-many", "one-to-many", "one-to-one"],
                    key="rel_card",
                )
            if st.form_submit_button("Add relation"):
                if rel_name.strip():
                    try:
                        onto.add_relation(
                            rel_name.strip(),
                            source=rel_source,
                            target=rel_target,
                            cardinality=rel_card,
                        )
                        flash(f"Added relation '{rel_name.strip()}'!")
                        st.rerun()
                    except ValidationError as e:
                        st.error(str(e))
                else:
                    st.warning("Please enter a relation name.")
    elif concept_names:
        st.info("Add at least 2 concepts before creating relations.")
    else:
        st.info("Add some concepts first!")

    if onto.relations:
        st.subheader("Existing relations")
        for rname, rel in sorted(onto.relations.items()):
            col_info, col_btn = st.columns([5, 1])
            with col_info:
                st.write(f"**{rel.name}**: {rel.source} -> {rel.target}  ({rel.cardinality})")
            with col_btn:
                if st.button("Remove", key=f"rm_rel_{rname}"):
                    onto.remove_relation(rname)
                    flash(f"Removed relation '{rname}'.")
                    st.rerun()

# ===================== INSTANCES TAB =====================
with tab_instances:
    concept_names = sorted(onto.concepts.keys())

    if concept_names:
        st.subheader("Add an instance")
        with st.form("add_inst_form", clear_on_submit=True):
            i1, i2 = st.columns(2)
            with i1:
                inst_name = st.text_input("Instance name *")
            with i2:
                inst_concept = st.selectbox("Of concept", concept_names, key="inst_concept")

            # Show property fields for the selected concept
            selected_concept = onto.concepts.get(inst_concept)
            prop_values = {}
            if selected_concept and selected_concept.properties:
                st.markdown(f"**Properties for {inst_concept}:**")
                for p in selected_concept.properties:
                    label = f"{p.name} ({p.data_type})" + (" *" if p.required else "")
                    prop_values[p.name] = st.text_input(label, key=f"inst_prop_{p.name}")

            if st.form_submit_button("Add instance"):
                if inst_name.strip():
                    try:
                        # Filter out empty values
                        props = {k: v for k, v in prop_values.items() if v.strip()}
                        onto.add_instance(
                            inst_name.strip(),
                            concept=inst_concept,
                            properties=props,
                        )
                        flash(f"Added instance '{inst_name.strip()}'!")
                        st.rerun()
                    except ValidationError as e:
                        st.error(str(e))
                else:
                    st.warning("Please enter an instance name.")
    else:
        st.info("Add some concepts first!")

    if onto.instances:
        st.subheader("Existing instances")
        for iname, inst in sorted(onto.instances.items()):
            with st.expander(f"{inst.name} (type: {inst.concept})"):
                if inst.properties:
                    for k, v in inst.properties.items():
                        st.write(f"- **{k}**: {v}")
                if st.button(f"Remove '{iname}'", key=f"rm_inst_{iname}"):
                    del onto.instances[iname]
                    flash(f"Removed instance '{iname}'.")
                    st.rerun()

# ===================== LEARN TAB =====================
with tab_learn:
    st.subheader("Ontology glossary")
    st.write("New to ontologies? Here are the key terms you'll encounter:")
    for term, definition in sorted(GLOSSARY.items()):
        with st.expander(term.title()):
            st.write(definition)
