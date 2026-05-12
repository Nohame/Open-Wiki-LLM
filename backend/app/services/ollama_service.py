import base64
import httpx
import json
from ..core.config import settings

COMPILE_PROMPT = """\
Tu es un assistant qui structure des textes bruts en pages wiki Markdown.

Voici un texte brut à structurer :

---
{text}
---

Génère une page wiki Markdown avec ce format EXACT (frontmatter inclus) :

```markdown
---
title: {title}
type: concept
status: draft
confidence: medium
sources: []
updated_at: {date}
tags: {tags}
---

# {title}

## Résumé

## Règles connues

## Points à confirmer
```

Réponds UNIQUEMENT avec le Markdown, sans commentaire ni explication.
"""


IMAGE_PROMPT = """\
Tu es un assistant qui analyse des images et structure leur contenu en pages wiki Markdown.

Analyse cette image et génère une page wiki Markdown avec ce format EXACT (frontmatter inclus) :

```markdown
---
title: {title}
type: concept
status: draft
confidence: medium
sources: []
updated_at: {date}
tags: {tags}
---

# {title}

## Description visuelle
(Décris ce que tu vois : schéma, photo, diagramme, capture d'écran...)

## Texte extrait
(Tout le texte lisible dans l'image, mot pour mot)

## Points à confirmer
```

Réponds UNIQUEMENT avec le Markdown, sans commentaire ni explication.
"""


def _strip_markdown_fence(text: str) -> str:
    """Strip outer ```markdown ... ``` wrapper that some models add."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        start = 1
        end = len(lines)
        if lines[-1].strip() == "```":
            end = -1
        return "\n".join(lines[start:end]).strip()
    return text


async def compile_image_to_markdown(
    image_bytes: bytes, title: str, tags: list[str], date: str
) -> str:
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = IMAGE_PROMPT.format(
        title=title,
        tags=json.dumps(tags, ensure_ascii=False),
        date=date,
    )
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_vision_model,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
            },
        )
        response.raise_for_status()
        return _strip_markdown_fence(response.json()["response"])


async def compile_to_markdown(text: str, title: str, tags: list[str], date: str) -> str:
    prompt = COMPILE_PROMPT.format(
        text=text,
        title=title,
        tags=json.dumps(tags, ensure_ascii=False),
        date=date,
    )
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
            },
        )
        response.raise_for_status()
        return _strip_markdown_fence(response.json()["response"])
