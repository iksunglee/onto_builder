"""OpenAI API client for the interview tool."""

from __future__ import annotations

import time
from openai import OpenAI, APIError, RateLimitError


def get_client(api_key: str) -> OpenAI:
    """Create an OpenAI client with the given API key."""
    return OpenAI(api_key=api_key)


def chat(
    client: OpenAI,
    messages: list[dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_retries: int = 2,
) -> str:
    """Send a chat completion with automatic retry on transient errors."""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except (RateLimitError, APIError) as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    raise last_error
