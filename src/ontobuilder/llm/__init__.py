"""LLM integration — auto-loads .env file for API key configuration."""

import os
from pathlib import Path


def _load_dotenv() -> None:
    """Load .env file from current directory if it exists."""
    env_file = Path(".env")
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            # Don't overwrite existing env vars
            if key not in os.environ:
                os.environ[key] = value


_load_dotenv()
