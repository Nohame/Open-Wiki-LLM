import httpx
from .base import LLMProvider

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, vision_model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.vision_model = vision_model

    async def generate(self, prompt: str) -> str:
        url = f"{GEMINI_BASE}/{self.model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    async def generate_with_image(self, prompt: str, image_b64: str) -> str:
        url = f"{GEMINI_BASE}/{self.vision_model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                url,
                json={
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
                        ]
                    }]
                },
            )
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
