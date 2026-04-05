"""Tests for OpenAI client module (unit tests, no API calls)."""

import os
import pytest


class TestGetApiKey:
    def test_from_argument(self):
        from ontobuilder.llm.openai_client import get_api_key
        assert get_api_key("sk-test123") == "sk-test123"

    def test_from_ontobuilder_env(self, monkeypatch):
        from ontobuilder.llm.openai_client import get_api_key
        monkeypatch.setenv("ONTOBUILDER_API_KEY", "sk-onto-key")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert get_api_key() == "sk-onto-key"

    def test_from_openai_env(self, monkeypatch):
        from ontobuilder.llm.openai_client import get_api_key
        monkeypatch.delenv("ONTOBUILDER_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-key")
        assert get_api_key() == "sk-openai-key"

    def test_priority_ontobuilder_over_openai(self, monkeypatch):
        from ontobuilder.llm.openai_client import get_api_key
        monkeypatch.setenv("ONTOBUILDER_API_KEY", "sk-priority")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fallback")
        assert get_api_key() == "sk-priority"

    def test_argument_overrides_env(self, monkeypatch):
        from ontobuilder.llm.openai_client import get_api_key
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
        assert get_api_key("sk-arg") == "sk-arg"

    def test_raises_when_no_key(self, monkeypatch):
        from ontobuilder.llm.openai_client import get_api_key
        monkeypatch.delenv("ONTOBUILDER_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="No OpenAI API key found"):
            get_api_key()


class TestGetModel:
    def test_default_model(self, monkeypatch):
        from ontobuilder.llm.openai_client import get_model
        monkeypatch.delenv("ONTOBUILDER_LLM_MODEL", raising=False)
        assert get_model() == "gpt-4o-mini"

    def test_custom_model(self, monkeypatch):
        from ontobuilder.llm.openai_client import get_model
        monkeypatch.setenv("ONTOBUILDER_LLM_MODEL", "gpt-4o")
        assert get_model() == "gpt-4o"


class TestSetApiKey:
    def test_set_api_key(self, monkeypatch):
        import ontobuilder.llm.openai_client as mod
        mod._client_instance = None
        mod.set_api_key("sk-new-key")
        assert os.environ.get("OPENAI_API_KEY") == "sk-new-key"
        assert mod._client_instance is None  # Client should be reset
        # Cleanup
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)


class TestBackendDetection:
    def test_forced_openai_backend(self, monkeypatch):
        from ontobuilder.llm.client import _get_backend
        monkeypatch.setenv("ONTOBUILDER_LLM_BACKEND", "openai")
        assert _get_backend() == "openai"

    def test_forced_litellm_backend(self, monkeypatch):
        from ontobuilder.llm.client import _get_backend
        monkeypatch.setenv("ONTOBUILDER_LLM_BACKEND", "litellm")
        assert _get_backend() == "litellm"

    def test_auto_detect(self, monkeypatch):
        from ontobuilder.llm.client import _get_backend
        monkeypatch.delenv("ONTOBUILDER_LLM_BACKEND", raising=False)
        # Should return something (depends on what's installed)
        backend = _get_backend()
        assert backend in ("litellm", "openai")


class TestDotenvLoading:
    def test_load_dotenv(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_ONTO_VAR=hello123\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TEST_ONTO_VAR", raising=False)

        from ontobuilder.llm import _load_dotenv
        _load_dotenv()
        assert os.environ.get("TEST_ONTO_VAR") == "hello123"

        # Cleanup
        monkeypatch.delenv("TEST_ONTO_VAR", raising=False)

    def test_no_dotenv_no_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ontobuilder.llm import _load_dotenv
        _load_dotenv()  # Should not raise

    def test_existing_env_not_overwritten(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_ONTO_KEEP=from_file\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TEST_ONTO_KEEP", "from_env")

        from ontobuilder.llm import _load_dotenv
        _load_dotenv()
        assert os.environ.get("TEST_ONTO_KEEP") == "from_env"
