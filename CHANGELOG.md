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
- Outils MCP `wiki_guide`, `wiki_write`, `wiki_delete` — découverte, création/MAJ et dépréciation de pages via MCP
- Ingestion texte via Ollama (configurable via OLLAMA_MODEL) — POST /api/ingest/text
- Modes strict et validated_only — POST /api/answer
- Ingestion fichiers (.md, .txt, .pdf, .docx) — POST /api/ingest/file avec extraction texte (pdfplumber, python-docx)
- Onglet "Fichiers" dans la page Ingest : drag-and-drop multi-fichiers, statut par fichier en temps réel, traitement séquentiel
- Limite taille fichier 10 Mo côté client et serveur (HTTP 413)

### Connu
- /mcp ne vérifie pas le header X-API-Key (bypass FastAPI middleware) — à corriger si API_KEY est utilisé en production
