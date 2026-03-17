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
Analyze this sample data and infer an ontology structure.

Data sample:
{data_sample}

Based on the columns, values, and patterns in this data:
1. Identify the main concepts (entities/classes)
2. Determine properties for each concept (from column names and value types)
3. Suggest relationships between concepts
4. Organize concepts in a hierarchy if appropriate

Be practical — focus on what the data actually represents."""


def interview_scoping_prompt(domain_hints: dict | None = None) -> list[dict[str, str]]:
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
            "content": INTERVIEW_RELATIONS.format(
                context=context, concepts=concept_list
            ),
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


def infer_prompt(data_sample: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": INFER_FROM_DATA.format(data_sample=data_sample)},
    ]
