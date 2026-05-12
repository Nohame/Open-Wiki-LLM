# Design — OpenWikiLLM

**Date :** 2026-05-11
**Statut :** approuvé
**Version :** 0.1.0

---

## Objectif

Plateforme open source qui transforme des sources brutes en un wiki Markdown structuré, lisible, versionnable et consultable par des agents IA via une API REST et un serveur MCP.

Philosophie :
```
sources brutes → extraction (Ollama) → pages Markdown → liens wiki → validation → consultation agents IA
```

---

## Décisions clés

| Point | Décision |
|---|---|
| LLM | Ollama (local), modèle configurable via `OLLAMA_MODEL` |
| Modèle par défaut | `mistral` |
| Usage | Projet open source générique |
| MCP | Monté dans FastAPI via ASGI sur `/mcp` |
| Auth | `X-API-Key` header, désactivable si `API_KEY` vide |
| DB | SQLite FTS5 pour la recherche texte |
| Ollama host | `host.docker.internal:11434` (Ollama tourne sur le host, pas dans Docker) |

---

## Architecture

### Structure du projet

```
openwikillm/
├── backend/
│   ├── app/
│   │   ├── api/          ← routes FastAPI (pages, search, ingest, index)
│   │   ├── core/         ← config (settings depuis .env), auth middleware
│   │   ├── mcp/          ← serveur FastMCP monté sur /mcp
│   │   ├── models/       ← schémas Pydantic
│   │   ├── services/     ← logique métier (wiki, search, ingest, ollama)
│   │   ├── storage/      ← lecture/écriture Markdown + SQLite FTS5
│   │   └── main.py       ← app FastAPI, montage MCP, middleware X-API-Key
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── wiki/                 ← pages Markdown (frontmatter YAML)
├── raw/                  ← sources brutes (pdf/, txt/, markdown/, imports/)
├── data/                 ← openwikillm.db, backlinks.json
├── docs/
│   ├── architecture/
│   ├── changelog/
│   ├── decisions/
│   ├── dev-notes/
│   └── specs/
├── docker-compose.yml
├── docker.sh
├── .env.example
├── CHANGELOG.md
└── README.md
```

### Flux de données

```
raw/ → POST /api/ingest/text → Ollama (OLLAMA_MODEL) → wiki/*.md
wiki/*.md → POST /api/index/rebuild → SQLite FTS5 → POST /api/search
wiki/*.md → GET /api/pages/{slug} → agents IA (via API ou MCP)
```

---

## Configuration `.env.example`

```env
APP_ENV=local
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8088

OPENWIKILLM_RAW_PATH=/app/raw
OPENWIKILLM_WIKI_PATH=/app/wiki
OPENWIKILLM_DATA_PATH=/app/data

OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=mistral

API_KEY=
```

---

## API REST

### MVP

```http
GET  /health
GET  /api/pages
GET  /api/pages/{slug}
POST /api/search
POST /api/ingest/text
POST /api/index/rebuild
```

### Futurs

```http
POST /api/compile
POST /api/answer
POST /api/audit
POST /api/contradictions/find
POST /api/export/openrag
```

---

## Serveur MCP

Monté dans FastAPI via `app.mount("/mcp", mcp.get_asgi_app())`.

### Tools MVP

```
wiki_search         → équivalent POST /api/search
wiki_read_page      → équivalent GET /api/pages/{slug}
wiki_list_pages     → équivalent GET /api/pages
wiki_rebuild_index  → équivalent POST /api/index/rebuild
```

### Resources

```
wiki://index
wiki://page/{slug}
wiki://concept/{slug}
wiki://contradictions
```

### Config Claude Code

```json
{
  "openwikillm": {
    "type": "http",
    "url": "http://localhost:8088/mcp"
  }
}
```

---

## Auth

Middleware FastAPI sur toutes les routes `/api/*` et `/mcp`.

- Header attendu : `X-API-Key: <valeur>`
- Si `API_KEY` est vide dans `.env` → auth désactivée (mode dev)
- Retourne `401 Unauthorized` si clé invalide

---

## Format des pages Markdown

```markdown
---
title: Nom de la page
type: concept         # concept | project | procedure | decision | note
status: draft         # draft | reviewed | validated | deprecated
confidence: medium    # low | medium | high
sources:
  - raw/imports/fichier-source.md
updated_at: 2026-05-11
tags:
  - tag1
  - tag2
---

# Nom de la page

## Résumé

## Règles connues

## Sources

## Pages liées

## Points à confirmer
```

---

## Recherche SQLite FTS5

```sql
CREATE VIRTUAL TABLE wiki_pages_fts USING fts5(
    slug,
    title,
    content,
    tags
);
```

---

## Docker

### docker-compose.yml

```yaml
services:
  openwikillm-api:
    build:
      context: ./backend
    container_name: openwikillm-api
    ports:
      - "8088:8088"
    volumes:
      - ./raw:/app/raw
      - ./wiki:/app/wiki
      - ./data:/app/data
      - ./docs:/app/docs
    env_file:
      - .env
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### docker.sh

Commandes : `start`, `stop`, `restart`, `ssh`.

---

## Tests

```
backend/tests/
├── test_health.py          ← GET /health sans et avec API key
├── test_wiki_service.py    ← lecture Markdown, parsing frontmatter
├── test_search.py          ← indexation FTS5, recherche
├── test_api_pages.py       ← GET /api/pages, GET /api/pages/{slug}
└── test_mcp_tools.py       ← wiki_search, wiki_read_page
```

Règle : chaque étape ajoute ses tests avant de passer à la suivante. Pas de mock DB — SQLite in-memory ou fichier temporaire.

```bash
pytest
```

---

## Plan de développement

### Étape 1 — Initialisation
- Structure du projet, Docker, `.env.example`
- FastAPI minimal + `GET /health`
- Middleware `X-API-Key`
- `docs/dev-notes/2026-05-11-initialisation.md`
- `CHANGELOG.md` + `README.md`

### Étape 2 — Wiki Markdown
- Lecture des fichiers `wiki/*.md`
- Parsing frontmatter YAML
- `GET /api/pages` + `GET /api/pages/{slug}`
- Tests

### Étape 3 — Index SQLite FTS5
- Création DB SQLite
- Indexation des pages
- `POST /api/index/rebuild` + `POST /api/search`
- Tests

### Étape 4 — MCP Server
- Montage FastMCP dans FastAPI
- `wiki_search`, `wiki_read_page`, `wiki_list_pages`, `wiki_rebuild_index`
- Documentation usage Claude Code

### Étape 5 — Ingestion simple
- `POST /api/ingest/text`
- Appel Ollama pour structurer en Markdown
- Sauvegarde dans `raw/imports/` + page draft dans `wiki/`
- Traçage des actions

### Étape 6 — Préparation IA
- Modes `strict` et `validated_only`
- Prompts de compilation
- Documentation d'usage agent

---

## Critères d'acceptation MVP

- `./docker.sh start` démarre le projet
- `curl http://localhost:8088/health` retourne `{"status": "ok"}`
- Pages Markdown lisibles via API et MCP
- Recherche FTS5 fonctionnelle
- Ingestion texte → page draft via Ollama
- Aucun commit sans validation explicite
