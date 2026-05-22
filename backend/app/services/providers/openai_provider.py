import httpx
from .base import LLMProvider

OPENAI_BASE = "https://api.openai.com/v1"


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, vision_model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.vision_model = vision_model

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{OPENAI_BASE}/chat/completions",
                headers=self._headers(),
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def generate_with_image(self, prompt: str, image_b64: str) -> str:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{OPENAI_BASE}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.vision_model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                        ],
                    }],
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
