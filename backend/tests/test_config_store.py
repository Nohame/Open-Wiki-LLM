import tempfile
from pathlib import Path
from unittest.mock import patch
from app.core.config import settings as env_settings
from app.core import config_store
from app.models.settings import (
    AppSettings, LLMConfig, OllamaConfig, OpenAIConfig,
    GeminiConfig, AnthropicConfig, CustomConfig, IngestConfig,
)


def test_app_settings_defaults():
    s = AppSettings()
    assert s.llm.provider == "ollama"
    assert s.llm.ollama.model == "mistral"
    assert s.llm.openai.api_key == ""
    assert s.ingest.max_text_chars == 30000


def test_app_settings_serializes_roundtrip():
    s = AppSettings()
    s.llm.provider = "openai"
    s.llm.openai.api_key = "sk-test"
    json_str = s.model_dump_json()
    s2 = AppSettings.model_validate_json(json_str)
    assert s2.llm.provider == "openai"
    assert s2.llm.openai.api_key == "sk-test"


def test_load_returns_default_when_no_file():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(env_settings, "data_path", tmp):
            config = config_store.load()
    assert config.llm.provider == "ollama"
    assert config.llm.ollama.base_url == env_settings.ollama_base_url


def test_save_and_load_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(env_settings, "data_path", tmp):
            s = config_store.load()
            s.llm.provider = "openai"
            s.llm.openai.api_key = "sk-test"
            config_store.save(s)
            loaded = config_store.load()
    assert loaded.llm.provider == "openai"
    assert loaded.llm.openai.api_key == "sk-test"


def test_load_bootstraps_from_env():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(env_settings, "data_path", tmp), \
             patch.object(env_settings, "ollama_model", "llama3"):
            config = config_store.load()
    assert config.llm.ollama.model == "llama3"
