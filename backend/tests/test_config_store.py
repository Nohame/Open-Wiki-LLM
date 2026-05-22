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
