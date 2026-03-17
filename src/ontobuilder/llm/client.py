"""LLM client abstraction using litellm + instructor."""

from __future__ import annotations

import os
from typing import Any, TypeVar

T = TypeVar("T")


def get_model() -> str:
    """Get the configured LLM model name."""
    return os.environ.get("ONTOBUILDER_LLM_MODEL", "gpt-4o-mini")


def get_api_key() -> str | None:
    """Get the configured API key."""
    return os.environ.get("ONTOBUILDER_API_KEY") or os.environ.get("OPENAI_API_KEY")


def create_client():
    """Create an instructor-patched LLM client."""
    try:
        import instructor
        from litellm import completion
    except ImportError:
        raise ImportError(
            "LLM features require extra dependencies. "
            "Install them with: pip install ontobuilder[llm]"
        )

    return instructor.from_litellm(completion)


def chat(
    messages: list[dict[str, str]],
    response_model: type[T] | None = None,
    **kwargs: Any,
) -> T | str:
    """Send a chat completion request.

    If response_model is provided, returns a structured (Pydantic) object.
    Otherwise returns the raw text response.
    """
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
