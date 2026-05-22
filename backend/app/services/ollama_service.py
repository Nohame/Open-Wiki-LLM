import base64
import json
from . import llm_service

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

IDENTIFY_RELATED_PROMPT = """\
Tu analyses un nouveau document pour identifier quelles pages wiki existantes
pourraient être liées ou nécessiter une mise à jour.

Titre du document : {title}

Document :
{text}

Index actuel du wiki :
{index}

Liste les slugs des pages wiki à charger (maximum 10).
Réponds UNIQUEMENT avec un JSON valide : ["slug1", "slug2"]
Si aucune page n'est liée, réponds : []
"""

MULTI_UPDATE_PROMPT = """\
Tu maintiens un wiki selon ce schéma :
{schema}

Nouveau document à intégrer :
Titre : {title} | Tags : {tags} | Date : {date}
{text}

Pages wiki existantes liées :
{related_pages}

Génère toutes les mises à jour nécessaires.
Pour chaque page à créer ou modifier, utilise ce format EXACT :

<page slug="{new_slug}">
[contenu complet de la page en Markdown avec frontmatter]
</page>

Règles :
- Crée une page principale pour le document source (slug : {new_slug}, type : concept)
- Si le document contient des concepts métier distincts, crée ou mets à jour les pages concept-- correspondantes (ex: concept--groove-tags, type : concept)
- Si le document mentionne des entités (personnes, fournisseurs, outils, systèmes), crée ou mets à jour les pages entity-- correspondantes (ex: entity--alizee, type : entity)
- Mets à jour les pages liées existantes : nouvelles informations, corrections, cross-refs [[slug]]
- N'inclus QUE les pages qui changent réellement
- Réponds UNIQUEMENT avec les balises <page>, sans commentaire
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
    provider = llm_service.get_provider()
    return _strip_markdown_fence(await provider.generate_with_image(prompt, image_b64))


async def compile_to_markdown(text: str, title: str, tags: list[str], date: str) -> str:
    prompt = COMPILE_PROMPT.format(
        text=text,
        title=title,
        tags=json.dumps(tags, ensure_ascii=False),
        date=date,
    )
    provider = llm_service.get_provider()
    return _strip_markdown_fence(await provider.generate(prompt))


async def identify_related_pages(text: str, title: str, index_content: str) -> list[str]:
    prompt = IDENTIFY_RELATED_PROMPT.format(
        title=title,
        text=text,
        index=index_content or "(index vide)",
    )
    provider = llm_service.get_provider()
    raw = (await provider.generate(prompt)).strip()
    try:
        slugs = json.loads(raw)
        if isinstance(slugs, list):
            return [s for s in slugs if isinstance(s, str)]
    except (json.JSONDecodeError, ValueError):
        pass
    return []


async def compile_multi_page(
    text: str,
    title: str,
    tags: list[str],
    date: str,
    schema: str,
    related_pages: dict[str, str],
    new_slug: str,
) -> str:
    pages_block = (
        "\n\n".join(f"=== {slug} ===\n{content}" for slug, content in related_pages.items())
        if related_pages
        else "(aucune page liée)"
    )
    prompt = MULTI_UPDATE_PROMPT.format(
        schema=schema,
        title=title,
        tags=json.dumps(tags, ensure_ascii=False),
        date=date,
        text=text,
        related_pages=pages_block,
        new_slug=new_slug,
    )
    provider = llm_service.get_provider()
    return await provider.generate(prompt)
