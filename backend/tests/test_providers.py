import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.providers.base import LLMProvider
from app.services.providers.ollama import OllamaProvider


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
