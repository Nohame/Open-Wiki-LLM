# Changelog

## [0.1.0] — Non publié

### Ajouté
- Initialisation du projet OpenWikiLLM
- Structure du projet, Docker Compose, docker.sh, .env.example
- API FastAPI minimale avec GET /health
- Middleware auth X-API-Key (désactivable si API_KEY vide)
- Lecture et parsing des pages Markdown avec frontmatter YAML
- GET /api/pages et GET /api/pages/{slug}
- Index de recherche SQLite FTS5 (wiki_pages_fts)
- POST /api/search avec sanitisation des requêtes FTS5 (OR, strip special chars)
- POST /api/index/rebuild
- Serveur MCP (FastMCP 3.x) monté sur /mcp avec wiki_search, wiki_read_page, wiki_list_pages, wiki_rebuild_index
- Ingestion texte via Ollama (configurable via OLLAMA_MODEL) — POST /api/ingest/text
- Modes strict et validated_only — POST /api/answer

### Connu
- /mcp ne vérifie pas le header X-API-Key (bypass FastAPI middleware) — à corriger si API_KEY est utilisé en production
