from pathlib import Path
from ..core.config import settings

DEFAULT_SCHEMA = """\
# Wiki Schema

## Format des pages

Frontmatter YAML obligatoire : title, type, status, confidence, sources, updated_at, tags
Sections standard : ## Résumé / ## Règles connues / ## Liens liés / ## Points à confirmer

## Types de pages

- `concept` : notion, règle, procédure métier
- `entity` : personne, fournisseur, outil, système
- `source` : résumé structuré d'un document source

## Conventions

- Cross-références entre pages : [[slug-de-la-page]]
- Slugs : minuscules, tirets, pas de caractères spéciaux
- status: draft = créé automatiquement / status: validated = relu manuellement
- Une page par concept ou entité distincte
"""


def load_or_create() -> str:
    schema_path = Path(settings.wiki_path) / "schema.md"
    if schema_path.exists():
        return schema_path.read_text(encoding="utf-8")
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(DEFAULT_SCHEMA, encoding="utf-8")
    return DEFAULT_SCHEMA
