"""Educational glossary and tips for ontology concepts."""

GLOSSARY: dict[str, str] = {
    "ontology": (
        "An ontology is a formal representation of knowledge in a domain. "
        "It defines the concepts (classes), their properties, and the relationships between them."
    ),
    "concept": (
        "A concept (or class) represents a category of things. For example, 'Animal' or 'Car'. "
        "Concepts can have parent concepts forming an 'is-a' hierarchy."
    ),
    "relation": (
        "A relation describes how two concepts are connected. For example, "
        "'Dog lives_in House' means dogs can live in houses."
    ),
    "property": (
        "A property is an attribute of a concept. For example, a 'Person' concept "
        "might have properties like 'name' (string) and 'age' (int)."
    ),
    "instance": (
        "An instance (or individual) is a specific example of a concept. "
        "For example, 'Rex' is an instance of the concept 'Dog'."
    ),
    "hierarchy": (
        "A hierarchy (or taxonomy) is a tree-like structure where concepts are organized "
        "from general to specific. 'Animal → Dog → Poodle' is a hierarchy."
    ),
    "is-a": (
        "An 'is-a' relationship means one concept is a specialization of another. "
        "'Dog is-a Animal' means every dog is also an animal. This is also called inheritance."
    ),
    "cardinality": (
        "Cardinality describes how many instances can participate in a relation. "
        "'one-to-many' means one source can relate to many targets (e.g., one Author writes many Books)."
    ),
    "domain": (
        "A domain is the subject area your ontology describes. "
        "Examples: healthcare, e-commerce, education, biology."
    ),
    "taxonomy": (
        "A taxonomy is a classification system — a hierarchy of concepts. "
        "It's the backbone of most ontologies."
    ),
}

TIPS: dict[str, str] = {
    "add_concept": (
        "Tip: You created a concept! Concepts are the building blocks of your ontology. "
        "Try adding a child concept with --parent to build a hierarchy."
    ),
    "add_concept_with_parent": (
        "Tip: You created an 'is-a' hierarchy! '{child}' is-a '{parent}' means "
        "every {child} is also a {parent}."
    ),
    "add_relation": (
        "Tip: Relations connect concepts. '{source}' → '{target}' via '{name}' "
        "describes how these concepts interact in your domain."
    ),
    "init": (
        "Tip: Your ontology is ready! Start by adding concepts that represent the key "
        "categories in your domain. Use 'onto concept add <name>'."
    ),
}


def get_definition(term: str) -> str | None:
    """Look up a term in the glossary (case-insensitive)."""
    return GLOSSARY.get(term.lower())


def get_tip(action: str, **kwargs: str) -> str:
    """Get an educational tip for an action."""
    template = TIPS.get(action, "")
    if template and kwargs:
        return template.format(**kwargs)
    return template
