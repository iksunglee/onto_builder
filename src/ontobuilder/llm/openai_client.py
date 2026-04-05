"""Direct OpenAI API client — lightweight alternative to litellm+instructor.

Uses the official openai Python SDK. Supports structured output via
JSON mode with Pydantic model parsing.

Usage:
    pip install openai

Configuration (in priority order):
    1. Pass api_key directly to functions
    2. ONTOBUILDER_API_KEY env var
    3. OPENAI_API_KEY env var

    Model override: ONTOBUILDER_LLM_MODEL env var (default: gpt-4o-mini)
"""

from __future__ import annotations

import json
import os
from typing import Any, TypeVar

T = TypeVar("T")

_client_instance = None


def get_api_key(api_key: str | None = None) -> str:
    """Resolve the API key from argument, env vars, or raise."""
    key = (
        api_key
        or os.environ.get("ONTOBUILDER_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    if not key:
        raise ValueError(
            "No OpenAI API key found. Set it via:\n"
            "  export OPENAI_API_KEY=sk-...\n"
            "  or export ONTOBUILDER_API_KEY=sk-...\n"
            "  or pass api_key= directly."
        )
    return key


def get_model() -> str:
    """Get the configured model name."""
    return os.environ.get("ONTOBUILDER_LLM_MODEL", "gpt-4o-mini")


def get_client(api_key: str | None = None):
    """Get or create a singleton OpenAI client."""
    global _client_instance
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "OpenAI client requires the openai package.\n"
            "Install it with: pip install openai"
        )

    if _client_instance is None:
        _client_instance = OpenAI(api_key=get_api_key(api_key))
    return _client_instance


def set_api_key(api_key: str) -> None:
    """Set the API key at runtime (resets the client)."""
    global _client_instance
    os.environ["OPENAI_API_KEY"] = api_key
    _client_instance = None


def chat(
    messages: list[dict[str, str]],
    response_model: type[T] | None = None,
    *,
    api_key: str | None = None,
    **kwargs: Any,
) -> T | str:
    """Send a chat completion request via OpenAI API.

    Args:
        messages: List of chat messages (role + content).
        response_model: Optional Pydantic model for structured output.
            If provided, uses JSON mode and parses the response.
        api_key: Optional API key override.
        **kwargs: Extra arguments forwarded to the API call.

    Returns:
        A Pydantic model instance if response_model is given, else a string.
    """
    client = get_client(api_key)
    model = kwargs.pop("model", get_model())

    if response_model is not None:
        return _structured_chat(client, model, messages, response_model, **kwargs)
    else:
        return _text_chat(client, model, messages, **kwargs)


def _text_chat(
    client,
    model: str,
    messages: list[dict[str, str]],
    **kwargs: Any,
) -> str:
    """Plain text completion."""
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        **kwargs,
    )
    return resp.choices[0].message.content


def _structured_chat(
    client,
    model: str,
    messages: list[dict[str, str]],
    response_model: type[T],
    max_retries: int = 2,
    **kwargs: Any,
) -> T:
    """Structured output via JSON mode with Pydantic parsing.

    Injects the JSON schema into the system prompt and requests
    ``response_format={"type": "json_object"}``.
    """
    schema = response_model.model_json_schema()
    schema_str = json.dumps(schema, indent=2)

    # Inject schema instruction into system message
    schema_instruction = (
        f"\n\nYou MUST respond with valid JSON matching this exact schema:\n"
        f"```json\n{schema_str}\n```\n"
        f"Respond ONLY with the JSON object, no extra text."
    )

    augmented_messages = list(messages)
    if augmented_messages and augmented_messages[0]["role"] == "system":
        augmented_messages[0] = {
            "role": "system",
            "content": augmented_messages[0]["content"] + schema_instruction,
        }
    else:
        augmented_messages.insert(0, {
            "role": "system",
            "content": "You are a helpful assistant." + schema_instruction,
        })

    last_error = None
    for attempt in range(max_retries + 1):
        resp = client.chat.completions.create(
            model=model,
            messages=augmented_messages,
            response_format={"type": "json_object"},
            **kwargs,
        )
        raw = resp.choices[0].message.content
        try:
            data = json.loads(raw)
            return response_model.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            last_error = e
            if attempt < max_retries:
                # Add error feedback for retry
                augmented_messages.append({"role": "assistant", "content": raw})
                augmented_messages.append({
                    "role": "user",
                    "content": f"That JSON was invalid: {e}. Please fix it and try again.",
                })

    raise ValueError(
        f"Failed to parse structured response after {max_retries + 1} attempts. "
        f"Last error: {last_error}"
    )
