"""Streamlit app — Dataset Analyzer → Ontology generator.

Upload a CSV or Excel file, inspect column statistics, and let an LLM
propose an initial OWL ontology based on the dataset's structure and content.
"""

import streamlit as st
import pandas as pd
import sys
import os
import io

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_here, "..", "src"))
sys.path.insert(0, os.path.join(_here, ".."))

from onto_interview.openai_client import get_client, chat
from onto_interview.ontology_builder import (
    extract_turtle_block,
    extract_text_block,
    parse_turtle_to_ontology,
    ontology_to_yaml,
)
from ontobuilder.serialization.yaml_io import save_yaml


# ── Prompt templates ─────────────────────────────────────────────────────────

ANALYZE_DATASET_SYSTEM = """\
You are an expert ontology engineer. You analyze datasets and design OWL ontologies
that faithfully capture the domain represented by the data.

Your methodology:
1. Examine column names, data types, cardinalities, and sample values
2. Identify entities (classes) — often represented by ID columns or categorical columns
3. Identify attributes (DatatypeProperties) — numeric/string/date columns
4. Identify relationships (ObjectProperties) — foreign-key-like columns linking entities
5. Identify hierarchies — columns that suggest parent-child groupings
6. Identify enumerations — low-cardinality categorical columns
7. Identify constraints — NOT NULL = required, unique = functional, etc.

Naming conventions:
- Class names: PascalCase, singular noun
- ObjectProperty names: camelCase, verb-first (e.g., belongsTo, hasCategory)
- DatatypeProperty names: camelCase, verb-first (e.g., hasPrice, hasName)
"""

PROPOSE_ONTOLOGY_PROMPT = """\
Below is a dataset profile. Analyze it and propose an OWL ontology.

## Dataset: {filename}
- Rows: {num_rows}
- Columns: {num_cols}

## Column Profiles
{column_profiles}

## Sample Rows (first 5)
{sample_rows}

---

Based on this dataset, propose an ontology by:

1. **Identify Classes**: What real-world entities does this dataset describe?
   Consider whether the dataset represents one entity type or multiple linked ones.
   Look for ID columns, categorical columns with few values, and foreign-key patterns.

2. **Identify Properties**: Map columns to DatatypeProperties (literal values)
   or ObjectProperties (links between classes).

3. **Identify Hierarchies**: Are there columns suggesting parent-child groupings?

4. **Identify Enumerations**: Which categorical columns should become enumeration classes?

5. **Identify Constraints**: Which properties are required (no nulls)?
   Which are functional (one value per instance)?

Return your analysis as a structured proposal with sections for Classes,
ObjectProperties, DatatypeProperties, Enumerations, Hierarchies, and Constraints.
Explain your reasoning for each design decision."""

GENERATE_FROM_DATASET_PROMPT = """\
Based on the dataset analysis and proposed ontology elements, generate a complete
OWL ontology in Turtle (.ttl) format.

## Dataset: {filename}
## Proposed Elements
{proposal}

Follow this EXACT file structure:

```turtle
@prefix {{prefix}}: <{{namespace_uri}}> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

# ── Ontology declaration ──────────────────────────────────────────────
# ── Abstract superclasses ─────────────────────────────────────────────
# ── Core classes ──────────────────────────────────────────────────────
# ── Enumeration classes ───────────────────────────────────────────────
# ── Enumeration individuals ───────────────────────────────────────────
# ── Object properties ─────────────────────────────────────────────────
# ── Datatype properties ───────────────────────────────────────────────
# ── Axioms ────────────────────────────────────────────────────────────
```

Rules:
- Every class MUST have: a owl:Class, rdfs:label, rdfs:comment
- Every property MUST have: rdfs:domain, rdfs:range, rdfs:comment
- Single-value properties should be owl:FunctionalProperty
- Required properties should have owl:minCardinality 1
- Low-cardinality categoricals become enumeration classes with owl:oneOf or named individuals
- Use appropriate xsd types: xsd:string, xsd:integer, xsd:float, xsd:boolean, xsd:date, xsd:dateTime

Return the Turtle inside a ```turtle code block.
After the code block, briefly explain key design decisions."""

GENERATE_SUMMARY_PROMPT = """\
Based on the Turtle ontology just generated, create an English summary suitable for
injection into an LLM system prompt. Return the summary inside a ```text code block.

Format:
```text
You reason over a {domain} ontology.

## Classes
- **ClassName**: description

## Properties
- **propertyName** (Domain → Range): description

## Enumeration values
- **ClassName** instances: value1, value2, ...

## Rules
- plain English constraint statements
```"""


# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Dataset → Ontology", page_icon="📊", layout="wide")
st.title("Dataset Analyzer → Ontology")
st.caption(
    "Upload a CSV or Excel file. The tool profiles its structure and uses an LLM "
    "to propose an initial OWL ontology."
)

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.environ.get("OPENAI_API_KEY", ""),
        help="Your OpenAI API key. Also reads from OPENAI_API_KEY env var.",
    )
    model = st.selectbox(
        "Model",
        ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "o4-mini"],
        index=0,
    )

    st.divider()

    phase_labels = {
        "upload": "📂 Upload",
        "profile": "📊 Profile",
        "proposal": "💡 Proposal",
        "ontology": "🏗️ Ontology",
        "refine": "✏️ Refine",
    }
    phase = st.session_state.get("phase", "upload")
    st.markdown(f"**Phase:** {phase_labels.get(phase, phase)}")

    st.divider()
    if st.button("🔄 Start Over", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.divider()
    st.header("How it works")
    st.markdown(
        "**Upload** → CSV or Excel file\n\n"
        "**Profile** → column types, stats, samples\n\n"
        "**Propose** → LLM identifies classes & properties\n\n"
        "**Generate** → OWL Turtle + English summary\n\n"
        "**Refine** → chat to adjust the ontology"
    )


# ── Session state ────────────────────────────────────────────────────────────

if "phase" not in st.session_state:
    st.session_state.phase = "upload"
    st.session_state.df = None
    st.session_state.filename = None
    st.session_state.profile_text = None
    st.session_state.sample_text = None
    st.session_state.proposal = None
    st.session_state.turtle = None
    st.session_state.summary = None
    st.session_state.ontology = None
    st.session_state.messages = []


# ── Helpers ──────────────────────────────────────────────────────────────────

def profile_dataframe(df: pd.DataFrame) -> str:
    """Build a text profile of each column."""
    lines = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        non_null = df[col].count()
        null_count = df[col].isna().sum()
        unique = df[col].nunique()
        total = len(df)

        line = f"### `{col}`\n"
        line += f"- dtype: {dtype}\n"
        line += f"- non-null: {non_null}/{total} ({100*non_null/total:.0f}%)\n"
        line += f"- unique values: {unique}\n"

        # Numeric stats
        if pd.api.types.is_numeric_dtype(df[col]):
            desc = df[col].describe()
            line += f"- min: {desc['min']}, max: {desc['max']}, mean: {desc['mean']:.2f}\n"

        # Categorical: show top values
        if unique <= 20 and unique > 0:
            top = df[col].value_counts().head(10)
            vals = ", ".join(f"{v} ({c})" for v, c in top.items())
            line += f"- values: {vals}\n"
        elif unique > 20:
            top = df[col].value_counts().head(5)
            vals = ", ".join(f"{v} ({c})" for v, c in top.items())
            line += f"- top 5: {vals}\n"

        lines.append(line)
    return "\n".join(lines)


def call_llm(system: str, user_prompt: str, temperature: float = 0.4) -> str:
    client = get_client(api_key)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_prompt},
    ]
    # Include conversation history for refinement
    for msg in st.session_state.messages:
        messages.append(msg)
    return chat(client, messages, model=model, temperature=temperature)


def call_llm_with_history(extra_messages: list[dict], temperature: float = 0.4) -> str:
    client = get_client(api_key)
    messages = [{"role": "system", "content": ANALYZE_DATASET_SYSTEM}]
    messages.extend(st.session_state.messages)
    messages.extend(extra_messages)
    return chat(client, messages, model=model, temperature=temperature)


# ── Upload section ───────────────────────────────────────────────────────────

upload_col, output_col = st.columns([3, 2])

with upload_col:
    if st.session_state.phase == "upload":
        st.subheader("Upload Dataset")
        uploaded = st.file_uploader(
            "Choose a CSV or Excel file",
            type=["csv", "xlsx", "xls", "tsv"],
            help="Upload the dataset you want to analyze.",
        )
        if uploaded:
            try:
                if uploaded.name.endswith((".xlsx", ".xls")):
                    df = pd.read_excel(uploaded)
                elif uploaded.name.endswith(".tsv"):
                    df = pd.read_csv(uploaded, sep="\t")
                else:
                    df = pd.read_csv(uploaded)

                st.session_state.df = df
                st.session_state.filename = uploaded.name
                st.session_state.profile_text = profile_dataframe(df)
                st.session_state.sample_text = df.head(5).to_markdown(index=False)
                st.session_state.phase = "profile"
                st.rerun()
            except Exception as e:
                st.error(f"Failed to read file: {e}")

    # ── Profile phase ────────────────────────────────────────────────────────

    if st.session_state.phase in ("profile", "proposal", "ontology", "refine"):
        df = st.session_state.df
        st.subheader(f"Dataset: {st.session_state.filename}")

        tab_preview, tab_stats, tab_profile = st.tabs(
            ["📋 Preview", "📈 Statistics", "🔍 Column Profile"]
        )

        with tab_preview:
            st.dataframe(df.head(50), use_container_width=True)
            st.caption(f"{len(df)} rows × {len(df.columns)} columns")

        with tab_stats:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Rows", len(df))
            col2.metric("Columns", len(df.columns))
            col3.metric("Numeric", len(df.select_dtypes(include="number").columns))
            col4.metric("Categorical", len(df.select_dtypes(include="object").columns))

            st.markdown("**Data Types**")
            dtype_counts = df.dtypes.value_counts()
            for dtype, count in dtype_counts.items():
                st.markdown(f"- `{dtype}`: {count} columns")

            st.markdown("**Missing Values**")
            missing = df.isna().sum()
            missing_cols = missing[missing > 0]
            if len(missing_cols) > 0:
                for col_name, count in missing_cols.items():
                    st.markdown(f"- `{col_name}`: {count} ({100*count/len(df):.1f}%)")
            else:
                st.markdown("No missing values!")

        with tab_profile:
            st.markdown(st.session_state.profile_text)

    # ── Proposal + Ontology chat ─────────────────────────────────────────────

    if st.session_state.phase in ("proposal", "ontology", "refine"):
        st.divider()
        st.subheader("Conversation")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if st.session_state.phase == "refine":
        if user_input := st.chat_input("Request changes to the ontology..."):
            st.session_state.messages.append({"role": "user", "content": user_input})

            from onto_interview.prompts import REFINE_TURTLE_PROMPT
            prompt = REFINE_TURTLE_PROMPT.format(
                current_turtle=st.session_state.turtle
            )
            with st.spinner("Refining ontology..."):
                response = call_llm_with_history(
                    [{"role": "user", "content": prompt + "\n\nUser request: " + user_input}],
                    temperature=0.3,
                )

            turtle = extract_turtle_block(response)
            if turtle:
                st.session_state.turtle = turtle
                try:
                    onto = parse_turtle_to_ontology(turtle)
                    st.session_state.ontology = onto
                except Exception:
                    pass

                # Regenerate summary
                with st.spinner("Updating summary..."):
                    summary_resp = call_llm_with_history(
                        [{"role": "user", "content": GENERATE_SUMMARY_PROMPT}],
                        temperature=0.3,
                    )
                summary = extract_text_block(summary_resp)
                if summary:
                    st.session_state.summary = summary

            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

# ── Output panel ─────────────────────────────────────────────────────────────

with output_col:
    st.subheader("Ontology Output")

    if st.session_state.phase == "profile":
        if not api_key:
            st.warning("Enter your OpenAI API key in the sidebar to proceed.")
        else:
            st.info("Dataset loaded. Click below to analyze and propose an ontology.")
            if st.button("💡 Analyze & Propose Ontology", use_container_width=True):
                prompt = PROPOSE_ONTOLOGY_PROMPT.format(
                    filename=st.session_state.filename,
                    num_rows=len(st.session_state.df),
                    num_cols=len(st.session_state.df.columns),
                    column_profiles=st.session_state.profile_text,
                    sample_rows=st.session_state.sample_text,
                )
                with st.spinner("Analyzing dataset and proposing ontology..."):
                    response = call_llm(
                        ANALYZE_DATASET_SYSTEM, prompt, temperature=0.4
                    )
                st.session_state.proposal = response
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.session_state.phase = "proposal"
                st.rerun()

    elif st.session_state.phase == "proposal":
        st.info("Review the proposal in the chat. Click below to generate the OWL ontology.")
        if st.button("🏗️ Generate OWL Ontology", use_container_width=True):
            prompt = GENERATE_FROM_DATASET_PROMPT.format(
                filename=st.session_state.filename,
                proposal=st.session_state.proposal,
            )
            with st.spinner("Generating OWL Turtle ontology..."):
                response = call_llm_with_history(
                    [{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
            turtle = extract_turtle_block(response)
            if turtle:
                st.session_state.turtle = turtle
                st.session_state.messages.append({"role": "assistant", "content": response})

                # Generate summary
                with st.spinner("Generating summary..."):
                    summary_resp = call_llm_with_history(
                        [{"role": "user", "content": GENERATE_SUMMARY_PROMPT}],
                        temperature=0.3,
                    )
                summary = extract_text_block(summary_resp)
                if summary:
                    st.session_state.summary = summary

                # Parse into Ontology
                try:
                    onto = parse_turtle_to_ontology(turtle)
                    st.session_state.ontology = onto
                except Exception:
                    pass

                st.session_state.phase = "refine"
                st.rerun()
            else:
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.warning("LLM didn't return a Turtle code block. Check the chat.")
                st.rerun()

    # Show generated ontology outputs
    if st.session_state.turtle:
        tab_turtle, tab_summary, tab_preview = st.tabs(
            ["🐢 Turtle (.ttl)", "📝 Prompt Summary", "👁️ Preview"]
        )

        with tab_turtle:
            st.code(st.session_state.turtle, language="turtle")
            st.download_button(
                "📥 Download .ttl",
                data=st.session_state.turtle,
                file_name="ontology.ttl",
                mime="text/turtle",
                use_container_width=True,
            )

        with tab_summary:
            if st.session_state.summary:
                st.markdown(st.session_state.summary)
                st.download_button(
                    "📥 Download summary.txt",
                    data=st.session_state.summary,
                    file_name="ontology_summary.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
            else:
                st.caption("Summary will appear after generation.")

        with tab_preview:
            if st.session_state.ontology:
                onto = st.session_state.ontology

                m1, m2, m3 = st.columns(3)
                m1.metric("Classes", len(onto.concepts))
                m2.metric("Relations", len(onto.relations))
                m3.metric(
                    "Properties",
                    sum(len(c.properties) for c in onto.concepts.values()),
                )

                with st.expander("Class Hierarchy", expanded=True):
                    st.code(onto.print_tree(), language=None)

                with st.expander("Classes & DatatypeProperties"):
                    for concept in onto.concepts.values():
                        parent_str = f" → {concept.parent}" if concept.parent else ""
                        st.markdown(f"**{concept.name}**{parent_str}")
                        if concept.description:
                            st.caption(concept.description)
                        if concept.properties:
                            for p in concept.properties:
                                req = " *(required/functional)*" if p.required else ""
                                st.markdown(f"- `{p.name}` : {p.data_type}{req}")
                        st.markdown("---")

                with st.expander("ObjectProperties (Relations)"):
                    if onto.relations:
                        for rel in onto.relations.values():
                            st.markdown(
                                f"**{rel.name}**: {rel.source} → {rel.target}"
                            )
                    else:
                        st.caption("No relations parsed.")
            else:
                st.caption("Preview will appear after generation.")

        # Export options
        st.divider()
        st.markdown("**Export**")

        exp1, exp2 = st.columns(2)
        with exp1:
            if st.session_state.ontology:
                yaml_str = ontology_to_yaml(st.session_state.ontology)
                st.download_button(
                    "📥 .onto.yaml",
                    data=yaml_str,
                    file_name="ontology.onto.yaml",
                    mime="text/yaml",
                    use_container_width=True,
                )
        with exp2:
            if st.button("💾 Save to project", use_container_width=True):
                ttl_path = os.path.join(_here, "..", "ontology.ttl")
                with open(ttl_path, "w", encoding="utf-8") as f:
                    f.write(st.session_state.turtle)

                if st.session_state.summary:
                    sum_path = os.path.join(_here, "..", "ontology_summary.txt")
                    with open(sum_path, "w", encoding="utf-8") as f:
                        f.write(st.session_state.summary)

                if st.session_state.ontology:
                    yaml_path = os.path.join(_here, "..", "ontology.onto.yaml")
                    save_yaml(st.session_state.ontology, yaml_path)

                st.success("Saved ontology.ttl, ontology_summary.txt, and ontology.onto.yaml")

        st.divider()
        st.caption("Type changes in the chat to refine the ontology.")

    elif st.session_state.phase == "upload":
        st.info("Upload a dataset to get started.")
