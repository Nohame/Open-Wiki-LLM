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
        return response.json()["response"]
