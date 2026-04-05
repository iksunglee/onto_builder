"""LLM client abstraction — auto-selects the best available backend.

Priority:
1. litellm + instructor (if installed) — supports many providers
2. openai SDK (if installed) — direct OpenAI API
3. Raises ImportError with install instructions

Configuration (env vars):
    ONTOBUILDER_PROVIDER — provider: openai, anthropic, local, custom
    OPENAI_API_KEY or ONTOBUILDER_API_KEY — API key (OpenAI/custom)
    ANTHROPIC_API_KEY — API key (Anthropic)
    ONTOBUILDER_LLM_MODEL — model name (default: gpt-4o-mini)
    ONTOBUILDER_LLM_BACKEND — force backend: "litellm" or "openai"
"""

from __future__ import annotations

import os
from typing import Any, TypeVar, overload

T = TypeVar("T")


def get_provider() -> str:
    """Get the configured provider name."""
    return os.environ.get("ONTOBUILDER_PROVIDER", "").lower()


def get_model() -> str:
    """Get the configured LLM model name."""
    return os.environ.get("ONTOBUILDER_LLM_MODEL", "gpt-4o-mini")


def get_api_key() -> str | None:
    """Get the configured API key (any provider)."""
    return (
        os.environ.get("ONTOBUILDER_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
    )


def is_configured() -> bool:
    """Check if any LLM provider is configured."""
    # Ensure .env is loaded (may not have been imported yet)
    from ontobuilder.llm import _load_dotenv
    _load_dotenv()

    if get_provider():
        return True
    if get_api_key():
        return True
    return False


def _get_backend() -> str:
    """Detect which backend to use."""
    forced = os.environ.get("ONTOBUILDER_LLM_BACKEND", "").lower()
    if forced in ("litellm", "openai"):
        return forced

    # Anthropic provider requires litellm
    provider = get_provider()
    if provider == "anthropic":
        try:
            import instructor  # noqa: F401
            import litellm  # noqa: F401

            return "litellm"
        except ImportError:
            raise ImportError(
                "Anthropic provider requires litellm. Install with:\n"
                "  pip install ontobuilder[llm]"
            )

    # Auto-detect: prefer litellm if available, fall back to openai
    try:
        import instructor  # noqa: F401
        import litellm  # noqa: F401

        return "litellm"
    except ImportError:
        pass

    try:
        import openai  # noqa: F401

        return "openai"
    except ImportError:
        pass

    raise ImportError(
        "No LLM backend found. Install one of:\n"
        "  pip install openai                    # lightweight, OpenAI only\n"
        "  pip install ontobuilder[llm]          # litellm + instructor, multi-provider"
    )


def create_client():
    """Create an instructor-patched LLM client (litellm backend only)."""
    try:
        import instructor
        from litellm import completion
    except ImportError:
        raise ImportError(
            "LLM features require extra dependencies. "
            "Install them with: pip install ontobuilder[llm]"
        )

    return instructor.from_litellm(completion)


@overload
def chat(
    messages: list[dict[str, str]],
    response_model: type[T],
    **kwargs: Any,
) -> T: ...


@overload
def chat(
    messages: list[dict[str, str]],
    response_model: None = None,
    **kwargs: Any,
) -> str: ...


def chat(
    messages: list[dict[str, str]],
    response_model: type[T] | None = None,
    **kwargs: Any,
) -> T | str:
    """Send a chat completion request.

    Auto-selects the best available backend (litellm or openai).
    If response_model is provided, returns a structured (Pydantic) object.
    Otherwise returns the raw text response.
    """
    backend = _get_backend()

    if backend == "openai":
        from ontobuilder.llm.openai_client import chat as openai_chat

        return openai_chat(messages, response_model=response_model, **kwargs)

    # litellm backend
    model = kwargs.pop("model", get_model())

    if response_model is not None:
        client = create_client()
        return client.chat.completions.create(
            model=model,
            messages=messages,
            response_model=response_model,
            **kwargs,
        )
    else:
        from litellm import completion

        resp = completion(model=model, messages=messages, **kwargs)
        return resp.choices[0].message.content
