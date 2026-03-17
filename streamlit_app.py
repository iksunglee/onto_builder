"""OntoBuilder - Visual Ontology Builder (Streamlit UI)."""

import json
import os
import streamlit as st
import networkx as nx
import yaml

from ontobuilder.core.ontology import Ontology
from ontobuilder.core.validation import ValidationError, VALID_DATA_TYPES
from ontobuilder.serialization.yaml_io import save_yaml, load_yaml
from ontobuilder.serialization.json_io import save_json
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
        '  rankdir=TB;',
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
        st.download_button("Download YAML", yaml_str, file_name="ontology.onto.yaml", mime="text/yaml")
    with col_j:
        json_str = json.dumps(onto.to_dict(), indent=2)
        st.download_button("Download JSON", json_str, file_name="ontology.json", mime="application/json")

    st.divider()

    # -- Stats --
    st.subheader("Stats")
    st.metric("Concepts", len(onto.concepts))
    st.metric("Relations", len(onto.relations))
    st.metric("Instances", len(onto.instances))

# ---------------------------------------------------------------------------
# Main area: tabs
# ---------------------------------------------------------------------------

tab_graph, tab_ai, tab_concepts, tab_relations, tab_instances, tab_learn = st.tabs(
    ["Graph", "AI Assistant", "Concepts", "Relations", "Instances", "Learn"]
)

# ===================== GRAPH TAB =====================
with tab_graph:
    if onto.concepts:
        dot = render_graph(onto)
        st.graphviz_chart(dot, use_container_width=True)
        st.caption("Blue dashed = is-a hierarchy | Green = relations | * = required property")
    else:
        st.info("Add some concepts to see the graph! Use the Concepts tab or apply a domain template from the sidebar.")

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
            return (
                "LLM dependencies not installed. Run:\n\n"
                "```\npip install ontobuilder[llm]\n```"
            )

    llm_err = _check_llm_deps()
    if llm_err:
        st.warning(llm_err)
    else:
        # --- API key config ---
        with st.expander("LLM Settings", expanded=not bool(
            os.environ.get("ONTOBUILDER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        )):
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
                    "step": "idle",       # idle | scoping | answering | reviewing | done
                    "questions": [],      # list of question strings
                    "answers": [],        # list of user answers
                    "suggestion": None,   # OntologySuggestion object
                    "selections": {},     # concept/relation name -> bool
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

                        result = chat(interview_scoping_prompt(), response_model=InterviewQuestions)
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
                        st.markdown(f"**Q{i+1}: {q}**")
                        ans = st.text_area(
                            f"Answer {i+1}",
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
                            f"Q: {q}\nA: {a}"
                            for q, a in zip(iv["questions"], iv["answers"])
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
                            r for r in rel_result.relations
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
                        st.info("The AI didn't suggest any new additions. Try a different request.")
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
                                    c for c in suggestion.concepts
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
                                                parent = c.parent if c.parent and c.parent in all_known else None
                                                onto.add_concept(
                                                    c.name, description=c.description, parent=parent
                                                )
                                                for p in c.properties:
                                                    dt = p.data_type if p.data_type in {
                                                        "string", "int", "float", "bool", "date"
                                                    } else "string"
                                                    try:
                                                        onto.add_property(
                                                            c.name, p.name,
                                                            data_type=dt, required=p.required,
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
                                                r.name, source=r.source,
                                                target=r.target, cardinality=r.cardinality,
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
                prop_concept = st.selectbox("To concept", sorted(onto.concepts.keys()), key="prop_concept")
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
                            prop_concept, prop_name.strip(),
                            data_type=prop_type, required=prop_req,
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
            with st.expander(f"{concept.name}" + (f" (child of {concept.parent})" if concept.parent else "")):
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
