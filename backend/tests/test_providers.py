import asyncio
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.providers.base import LLMProvider
from app.services.providers.ollama import OllamaProvider
from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.custom_provider import CustomProvider
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.anthropic_provider import AnthropicProvider
from app.core.config import settings as env_settings
from app.core import config_store
from app.models.settings import AppSettings
from app.services import llm_service


def test_llmprovider_is_abstract():
    import inspect
    assert inspect.isabstract(LLMProvider)


def _mock_httpx(json_return: dict):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = json_return
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    return mock_client, mock_resp


def test_ollama_generate():
    mock_client, _ = _mock_httpx({"response": "generated"})
    with patch("app.services.providers.ollama.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        provider = OllamaProvider("http://localhost:11434", "mistral", "llava")
        result = asyncio.run(provider.generate("hello"))
    assert result == "generated"
    mock_client.post.assert_called_once_with(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": "hello", "stream": False},
    )


def test_ollama_generate_with_image():
    mock_client, _ = _mock_httpx({"response": "image result"})
    with patch("app.services.providers.ollama.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        provider = OllamaProvider("http://localhost:11434", "mistral", "llava")
        result = asyncio.run(provider.generate_with_image("describe", "abc123"))
    assert result == "image result"
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[1]["json"]["model"] == "llava"
    assert call_kwargs[1]["json"]["images"] == ["abc123"]


def test_openai_generate():
    mock_client, _ = _mock_httpx(
        {"choices": [{"message": {"content": "answer"}}]}
    )
    with patch("app.services.providers.openai_provider.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        provider = OpenAIProvider("sk-test", "gpt-4o", "gpt-4o")
        result = asyncio.run(provider.generate("hello"))
    assert result == "answer"
    call_json = mock_client.post.call_args[1]["json"]
    assert call_json["model"] == "gpt-4o"
    assert call_json["messages"][0]["content"] == "hello"


def test_openai_generate_with_image():
    mock_client, _ = _mock_httpx(
        {"choices": [{"message": {"content": "img answer"}}]}
    )
    with patch("app.services.providers.openai_provider.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        provider = OpenAIProvider("sk-test", "gpt-4o", "gpt-4o")
        result = asyncio.run(provider.generate_with_image("describe", "b64data"))
    assert result == "img answer"
    content = mock_client.post.call_args[1]["json"]["messages"][0]["content"]
    assert isinstance(content, list)
    types = [item["type"] for item in content]
    assert "text" in types
    assert "image_url" in types


def test_custom_generate_uses_configured_base_url():
    mock_client, _ = _mock_httpx(
        {"choices": [{"message": {"content": "custom answer"}}]}
    )
    with patch("app.services.providers.custom_provider.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        provider = CustomProvider("https://openrouter.ai/api/v1", "sk-or", "mistral", "mistral")
        result = asyncio.run(provider.generate("hello"))
    assert result == "custom answer"
    url = mock_client.post.call_args[0][0]
    assert url == "https://openrouter.ai/api/v1/chat/completions"


def test_gemini_generate():
    mock_client, _ = _mock_httpx(
        {"candidates": [{"content": {"parts": [{"text": "gemini answer"}]}}]}
    )
    with patch("app.services.providers.gemini_provider.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        provider = GeminiProvider("gemini-key", "gemini-1.5-pro", "gemini-1.5-pro")
        result = asyncio.run(provider.generate("hello"))
    assert result == "gemini answer"
    url = mock_client.post.call_args[0][0]
    assert "gemini-key" in url
    assert "gemini-1.5-pro" in url


def test_anthropic_generate():
    mock_client, _ = _mock_httpx(
        {"content": [{"text": "claude answer"}]}
    )
    with patch("app.services.providers.anthropic_provider.httpx.AsyncClient") as MockCls:
        MockCls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockCls.return_value.__aexit__ = AsyncMock(return_value=None)
        provider = AnthropicProvider("sk-ant-test", "claude-opus-4-7", "claude-opus-4-7")
        result = asyncio.run(provider.generate("hello"))
    assert result == "claude answer"
    headers = mock_client.post.call_args[1]["headers"]
    assert headers["x-api-key"] == "sk-ant-test"
    assert headers["anthropic-version"] == "2023-06-01"


def _config_with_provider(provider_name: str, **kwargs) -> AppSettings:
    s = AppSettings()
    s.llm.provider = provider_name
    for k, v in kwargs.items():
        setattr(getattr(s.llm, provider_name), k, v)
    return s


def test_get_provider_returns_ollama_by_default():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(env_settings, "data_path", tmp):
            provider = llm_service.get_provider()
    assert isinstance(provider, OllamaProvider)


def test_get_provider_returns_openai():
    s = _config_with_provider("openai", api_key="sk-test")
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(env_settings, "data_path", tmp):
            config_store.save(s)
            provider = llm_service.get_provider()
    assert isinstance(provider, OpenAIProvider)


def test_get_provider_returns_custom():
    s = _config_with_provider("custom", base_url="https://openrouter.ai/api/v1")
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(env_settings, "data_path", tmp):
            config_store.save(s)
            provider = llm_service.get_provider()
    assert isinstance(provider, CustomProvider)
