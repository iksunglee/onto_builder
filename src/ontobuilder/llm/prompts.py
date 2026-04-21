"""Prompt templates for LLM interactions."""

SYSTEM_PROMPT = """\
You are an ontology design assistant. You help users build ontologies — structured \
representations of knowledge with concepts (classes), properties, and relationships.

Be friendly, concise, and educational. When suggesting ontology elements, explain \
why they're useful. Use simple language — the user may be new to ontologies."""

INTERVIEW_SCOPING = """\
The user wants to build an ontology for their domain. Ask 2-3 focused questions to \
understand:
1. What domain/subject area is this for?
2. What is the main purpose of this ontology?
3. What are the most important things (entities/concepts) in this domain?

Keep questions simple and beginner-friendly."""

INTERVIEW_CONCEPTS = """\
Based on the user's answers, suggest concepts (classes) for their ontology.

User's domain description:
{context}

Suggest 5-10 concepts organized in a hierarchy (with parent-child relationships). \
Include relevant properties for each concept. Focus on the most important and \
commonly used concepts first."""

INTERVIEW_RELATIONS = """\
Given these concepts, suggest relationships between them.

Concepts:
{concepts}

User's domain:
{context}

Suggest meaningful relations that capture how these concepts interact."""

ENHANCE_EXISTING = """\
The user has an existing ontology and wants suggestions to improve or expand it.

Current ontology:
  Name: {name}
  Description: {description}

Existing concepts:
{concepts}

Existing relations:
{relations}

User's request:
{user_request}

Based on the existing structure and the user's request:
1. Suggest new concepts that would complement the existing ones
2. Suggest new relations between existing and/or new concepts
3. Suggest new properties for existing or new concepts
4. Organize any new concepts in the existing hierarchy where appropriate

IMPORTANT: Do NOT re-suggest concepts or relations that already exist. Only suggest NEW additions. \
Make sure any parent references point to concepts that either already exist or are in your suggestions."""

INFER_FROM_DATA = """\
Analyze this data and infer an ontology structure.

Data sample:
{data_sample}

{analysis_context}

Based on the actual data values and patterns:
1. Identify the main concepts (entities/classes) — look at what each row represents
2. Determine properties for each concept from column names, value types, and actual values
3. Find relationships between concepts — especially:
   - Comma-separated or delimited values in a cell → separate entity with many-to-many relation
   - Columns that reference other entities (company names, category names, IDs) → separate concept with relation
   - Nested or repeated structures → child concepts
4. Organize concepts in a hierarchy if appropriate

Be practical — focus on what the data actually represents, not just literal column names.
When a column contains lists of items (e.g. ingredients, tags, roles), model those items as a separate concept linked by a relation, not as a flat string property."""

INFER_SUBCATEGORIES = """\
The user has confirmed these top-level concepts for their ontology:

{confirmed_concepts}

Here is the data:
{data_sample}

{analysis_context}

Based on the ACTUAL VALUES in the data, suggest specific sub-categories (child concepts) \
for each confirmed concept where it makes sense. For example:
- If there's a "Category" concept and the data has values like "Electronics", "Sports", "Home" \
→ suggest those as child concepts of Category
- If there's a "PaymentMethod" concept with values "Credit Card", "PayPal", "Bank Transfer" \
→ suggest those as child concepts of PaymentMethod
- If there's a "CustomerTier" concept with values "Gold", "Silver", "Bronze" \
→ suggest those as child concepts of CustomerTier

Rules:
- Only suggest sub-categories clearly present in the data values
- Each sub-category MUST have its parent set to one of the confirmed concepts
- Do NOT re-suggest the confirmed concepts themselves
- Focus on categorical/enum-like values, not unique values like names or IDs
- Keep descriptions brief — one line explaining what the category represents
- Do NOT add properties to sub-categories (they inherit from the parent)"""


SCENARIO_SYSTEM = """\
You are an Ontology Reasoning Engine.

Your role is to interpret user queries and generate \
structured reasoning based on an ontology.

You MUST think in terms of:
- Entities (objects, actors)
- Relationships (connections between entities)
- Attributes (quantitative or qualitative properties)
- Constraints (rules, limitations, regulations)
- Optimization goals (efficiency, cost, quality, time, outcome)

---

### Step 1 — Identify Scenario Type

Classify the request into one of the following:
- Planning (create something new)
- Allocation (assign resources)
- Optimization (improve outcome)
- Diagnosis (identify problem)
- Simulation (what-if scenario)

---

### Step 2 — Extract Ontology Components

From the input, extract:

1. Entities:
2. Relationships:
3. Attributes:
4. Constraints:
5. Goals:

---

### Step 3 — Map to Ontology Graph

Translate into graph structure:

(Entity)-[RELATIONSHIP]->(Entity)

Include weights, conditions, or context where applicable.

---

### Step 4 — Reason Over Graph

Perform reasoning such as:
- Path finding (how things connect)
- Trade-off analysis
- Constraint satisfaction
- Impact propagation (if X changes → what happens?)

---

### Step 5 — Generate Output in 3 Layers

1. Human-readable explanation
2. Structured ontology output (JSON or graph)
3. Actionable recommendations

---

### Step 6 — If Applicable, Convert to Optimization Logic

If the problem involves improvement:
- Translate into measurable variables
- Suggest how it could be modeled (ML, rules, scoring)

---

IMPORTANT:
- Always think in SYSTEMS, not isolated answers
- Always connect decisions back to ontology relationships
- When uncertain, propose multiple possible interpretations"""

SCENARIO_ANALYZE = """\
Analyze the following scenario and build a complete ontology from it.

Scenario:
{scenario}

{existing_context}

Follow your 6-step reasoning process. For Step 5, return the structured \
ontology output as a list of concepts (with properties) and relations \
between them. Organize concepts into a hierarchy where it makes sense.

Focus on:
- The key entities/actors in this scenario
- How they relate to each other
- What attributes/properties matter for each entity
- What constraints or rules govern the system
- What goals or optimization targets exist"""

SCENARIO_REFINE = """\
The user has a scenario-based ontology and wants to refine it.

Current ontology:
{ontology_state}

Original scenario type: {scenario_type}

The user's follow-up:
{user_message}

Reason over the existing ontology graph and the user's request. \
Apply your 6-step process to determine what changes, additions, \
or restructuring is needed. Return updated concepts and relations."""


def interview_scoping_prompt(
    domain_hints: dict[str, object] | None = None,
) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    content = INTERVIEW_SCOPING
    if domain_hints:
        content += f"\n\nDomain hints: {domain_hints}"
    messages.append({"role": "user", "content": content})
    return messages


def interview_concepts_prompt(context: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": INTERVIEW_CONCEPTS.format(context=context)},
    ]


def interview_relations_prompt(context: str, concepts: list[str]) -> list[dict[str, str]]:
    concept_list = "\n".join(f"- {c}" for c in concepts)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": INTERVIEW_RELATIONS.format(context=context, concepts=concept_list),
        },
    ]


def enhance_existing_prompt(
    name: str,
    description: str,
    concepts: list[str],
    relations: list[str],
    user_request: str,
) -> list[dict[str, str]]:
    concept_list = "\n".join(f"- {c}" for c in concepts) if concepts else "(none yet)"
    relation_list = "\n".join(f"- {r}" for r in relations) if relations else "(none yet)"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": ENHANCE_EXISTING.format(
                name=name,
                description=description or "(no description)",
                concepts=concept_list,
                relations=relation_list,
                user_request=user_request,
            ),
        },
    ]


def infer_subcategories_prompt(
    confirmed_concepts: list[str],
    data_sample: str,
    analysis_context: str = "",
) -> list[dict[str, str]]:
    """Build prompt for suggesting sub-categories based on confirmed concepts + data."""
    concept_list = "\n".join(f"- {c}" for c in confirmed_concepts)
    ctx = ""
    if analysis_context:
        ctx = f"Additional analysis from the full dataset:\n{analysis_context}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": INFER_SUBCATEGORIES.format(
                confirmed_concepts=concept_list,
                data_sample=data_sample,
                analysis_context=ctx,
            ),
        },
    ]


def infer_prompt(
    data_sample: str, analysis_context: str = ""
) -> list[dict[str, str]]:
    ctx = ""
    if analysis_context:
        ctx = f"Additional analysis from the full dataset:\n{analysis_context}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": INFER_FROM_DATA.format(
                data_sample=data_sample, analysis_context=ctx
            ),
        },
    ]
