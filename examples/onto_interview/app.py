"""Streamlit app — OWL ontology interview tool.

Guides users through a conversational interview to build a proper OWL ontology
in Turtle (.ttl) format, following the methodology from ONTOLOGY.md.
"""

import streamlit as st
import sys
import os

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_here, "..", "src"))
sys.path.insert(0, os.path.join(_here, ".."))

from onto_interview.openai_client import get_client, chat
from onto_interview.prompts import (
    SYSTEM_PROMPT,
    INTERVIEW_OPENER,
    EXTRACTION_PROMPT,
    GENERATE_TURTLE_PROMPT,
    GENERATE_SUMMARY_PROMPT,
    VALIDATION_CHECKLIST,
    REFINE_TURTLE_PROMPT,
)
from onto_interview.ontology_builder import (
    extract_turtle_block,
    extract_text_block,
    parse_turtle_to_ontology,
    ontology_to_yaml,
)
from ontobuilder.serialization.yaml_io import save_yaml

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="OWL Ontology Interview", page_icon="🦉", layout="wide")
st.title("OWL Ontology Interview")
st.caption(
    "Build a domain ontology through conversation — outputs OWL Turtle (.ttl) "
    "with classes, properties, axioms, and an LLM prompt summary."
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

    # Phase indicator
    phase_labels = {
        "interview": "💬 Interview",
        "extraction": "🔍 Extraction",
        "generation": "🏗️ Generation",
        "review": "✅ Review & Refine",
    }
    phase = st.session_state.get("phase", "interview")
    st.markdown(f"**Phase:** {phase_labels.get(phase, phase)}")

    st.divider()
    if st.button("🔄 New Interview", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.divider()
    st.header("Methodology")
    st.markdown(
        "**Interview** → understand the domain\n\n"
        "**Extract** → identify classes, properties, axioms\n\n"
        "**Generate** → produce OWL Turtle + English summary\n\n"
        "**Validate** → self-check against OWL rules\n\n"
        "**Refine** → iterate on the ontology"
    )

# ── Session state ────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.api_messages = []
    st.session_state.phase = "interview"
    st.session_state.started = False
    st.session_state.turtle = None
    st.session_state.summary = None
    st.session_state.validation = None
    st.session_state.ontology = None
    st.session_state.extraction = None

# ── Helpers ──────────────────────────────────────────────────────────────────


def add_assistant_message(content: str):
    st.session_state.messages.append({"role": "assistant", "content": content})
    st.session_state.api_messages.append({"role": "assistant", "content": content})


def add_user_message(content: str):
    st.session_state.messages.append({"role": "user", "content": content})
    st.session_state.api_messages.append({"role": "user", "content": content})


def call_llm(extra_messages: list[dict] | None = None, temperature: float = 0.7) -> str:
    client = get_client(api_key)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(st.session_state.api_messages)
    if extra_messages:
        messages.extend(extra_messages)
    return chat(client, messages, model=model, temperature=temperature)


def run_extraction():
    """Ask LLM to extract domain elements from the conversation."""
    with st.spinner("Extracting domain elements..."):
        response = call_llm(
            [{"role": "user", "content": EXTRACTION_PROMPT}],
            temperature=0.4,
        )
    st.session_state.extraction = response
    st.session_state.phase = "extraction"
    add_assistant_message(response)


def run_generation():
    """Ask LLM to generate OWL Turtle from the confirmed elements."""
    with st.spinner("Generating OWL Turtle ontology..."):
        response = call_llm(
            [{"role": "user", "content": GENERATE_TURTLE_PROMPT}],
            temperature=0.3,
        )
    turtle = extract_turtle_block(response)
    if turtle:
        st.session_state.turtle = turtle
        add_assistant_message(response)

        # Generate English summary
        with st.spinner("Generating LLM prompt summary..."):
            summary_response = call_llm(
                [{"role": "user", "content": GENERATE_SUMMARY_PROMPT}],
                temperature=0.3,
            )
        summary = extract_text_block(summary_response)
        if summary:
            st.session_state.summary = summary
        add_assistant_message(summary_response)

        # Run validation
        with st.spinner("Running validation checklist..."):
            validation_response = call_llm(
                [{"role": "user", "content": VALIDATION_CHECKLIST}],
                temperature=0.2,
            )
        st.session_state.validation = validation_response
        add_assistant_message(validation_response)

        # Parse into ontobuilder Ontology for display
        try:
            onto = parse_turtle_to_ontology(turtle)
            st.session_state.ontology = onto
        except Exception:
            pass

        st.session_state.phase = "review"
        return True
    else:
        add_assistant_message(response)
        st.warning("LLM didn't return a Turtle code block. Continuing...")
        return False


def run_refinement(user_request: str):
    """Refine the ontology based on user feedback."""
    prompt = REFINE_TURTLE_PROMPT.format(current_turtle=st.session_state.turtle)
    with st.spinner("Refining ontology..."):
        response = call_llm(
            [{"role": "user", "content": prompt + "\n\nUser request: " + user_request}],
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
        with st.spinner("Updating prompt summary..."):
            summary_response = call_llm(
                [{"role": "user", "content": GENERATE_SUMMARY_PROMPT}],
                temperature=0.3,
            )
        summary = extract_text_block(summary_response)
        if summary:
            st.session_state.summary = summary

    add_assistant_message(response)


# ── Validate API key ─────────────────────────────────────────────────────────

if not api_key:
    st.info("Enter your OpenAI API key in the sidebar to start.")
    st.stop()

# ── Start interview ──────────────────────────────────────────────────────────

if not st.session_state.started:
    with st.spinner("Starting interview..."):
        client = get_client(api_key)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": INTERVIEW_OPENER},
        ]
        opener = chat(client, messages, model=model)
    add_assistant_message(opener)
    st.session_state.started = True

# ── Layout ───────────────────────────────────────────────────────────────────

chat_col, onto_col = st.columns([3, 2])

# ── Chat column ──────────────────────────────────────────────────────────────

with chat_col:
    st.subheader("Conversation")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Your answer..."):
        add_user_message(user_input)
        with st.chat_message("user"):
            st.markdown(user_input)

        if st.session_state.phase == "review":
            with st.chat_message("assistant"):
                run_refinement(user_input)
                st.rerun()
        elif st.session_state.phase == "extraction":
            # User confirming or modifying extractions
            generate_triggers = {"yes", "confirm", "looks good", "correct", "generate", "go ahead", "proceed", "approved", "lgtm"}
            if any(t in user_input.lower() for t in generate_triggers):
                with st.chat_message("assistant"):
                    run_generation()
                    st.rerun()
            else:
                with st.chat_message("assistant"):
                    response = call_llm()
                    add_assistant_message(response)
                    st.rerun()
        else:
            # Interview phase
            extract_triggers = {"done", "that's all", "extract", "ready", "let's build", "generate", "go ahead"}
            if any(t in user_input.lower() for t in extract_triggers):
                with st.chat_message("assistant"):
                    run_extraction()
                    st.rerun()
            else:
                with st.chat_message("assistant"):
                    response = call_llm()
                    add_assistant_message(response)
                    st.rerun()

# ── Ontology panel ───────────────────────────────────────────────────────────

with onto_col:
    st.subheader("Ontology Output")

    if st.session_state.phase == "interview":
        st.info(
            "Answer the interview questions to describe your domain. "
            "When ready, click **Extract Elements** or type 'done'."
        )
        if st.button("🔍 Extract Elements", use_container_width=True):
            run_extraction()
            st.rerun()

    elif st.session_state.phase == "extraction":
        st.info(
            "Review the extracted elements in the chat. "
            "Confirm them or request changes, then click **Generate Ontology**."
        )
        if st.button("🏗️ Generate OWL Ontology", use_container_width=True):
            run_generation()
            st.rerun()

    # Show Turtle output
    if st.session_state.turtle:
        tab_turtle, tab_summary, tab_validation, tab_preview = st.tabs(
            ["🐢 Turtle (.ttl)", "📝 Prompt Summary", "✅ Validation", "👁️ Preview"]
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

        with tab_validation:
            if st.session_state.validation:
                st.markdown(st.session_state.validation)
            else:
                st.caption("Validation results will appear after generation.")

        with tab_preview:
            if st.session_state.ontology:
                onto = st.session_state.ontology

                col1, col2, col3 = st.columns(3)
                col1.metric("Classes", len(onto.concepts))
                col2.metric("Relations", len(onto.relations))
                col3.metric(
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
                        st.caption("No relations parsed (check Turtle tab for full detail).")
            else:
                st.caption("Preview will appear after generation.")

        # Export options
        st.divider()
        st.markdown("**Export**")

        export_cols = st.columns(2)
        with export_cols[0]:
            if st.session_state.ontology:
                yaml_str = ontology_to_yaml(st.session_state.ontology)
                st.download_button(
                    "📥 .onto.yaml",
                    data=yaml_str,
                    file_name="ontology.onto.yaml",
                    mime="text/yaml",
                    use_container_width=True,
                )
        with export_cols[1]:
            if st.button("💾 Save to project", use_container_width=True):
                # Save Turtle
                ttl_path = os.path.join(_here, "..", "ontology.ttl")
                with open(ttl_path, "w", encoding="utf-8") as f:
                    f.write(st.session_state.turtle)

                # Save summary
                if st.session_state.summary:
                    sum_path = os.path.join(_here, "..", "ontology_summary.txt")
                    with open(sum_path, "w", encoding="utf-8") as f:
                        f.write(st.session_state.summary)

                # Save YAML if we have an ontology
                if st.session_state.ontology:
                    yaml_path = os.path.join(_here, "..", "ontology.onto.yaml")
                    save_yaml(st.session_state.ontology, yaml_path)

                st.success("Saved ontology.ttl, ontology_summary.txt, and ontology.onto.yaml")

        st.divider()
        st.caption("Type changes in the chat to refine the ontology.")
