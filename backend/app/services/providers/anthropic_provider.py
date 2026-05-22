import httpx
from .base import LLMProvider

ANTHROPIC_BASE = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, vision_model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.vision_model = vision_model

    def _headers(self) -> dict:
        return {"x-api-key": self.api_key, "anthropic-version": ANTHROPIC_VERSION}

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{ANTHROPIC_BASE}/messages",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]

    async def generate_with_image(self, prompt: str, image_b64: str) -> str:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{ANTHROPIC_BASE}/messages",
                headers=self._headers(),
                json={
                    "model": self.vision_model,
                    "max_tokens": 4096,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                            {"type": "text", "text": prompt},
                        ],
                    }],
                },
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]
