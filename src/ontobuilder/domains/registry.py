"""Registry for domain builders."""

from __future__ import annotations

from ontobuilder.domains.base import DomainBuilder


_registry: dict[str, DomainBuilder] = {}


def register(builder: DomainBuilder) -> None:
    """Register a domain builder."""
    _registry[builder.name] = builder


def get_builder(name: str) -> DomainBuilder | None:
    """Get a domain builder by name."""
    _ensure_builtins()
    return _registry.get(name)


def list_builders() -> list[DomainBuilder]:
    """List all registered domain builders."""
    _ensure_builtins()
    return list(_registry.values())


_loaded = False


def _ensure_builtins() -> None:
    """Lazily load built-in domain builders."""
    global _loaded
    if _loaded:
        return
    _loaded = True

    from ontobuilder.domains.ecommerce import EcommerceDomainBuilder
    from ontobuilder.domains.healthcare import HealthcareDomainBuilder

    register(EcommerceDomainBuilder())
    register(HealthcareDomainBuilder())
