# OpenWikiLLM

Plateforme wiki open source qui transforme des sources brutes en pages Markdown structurées, consultables par des agents IA via une API REST et un serveur MCP.

Contrairement à un RAG classique qui découpe en chunks, OpenWikiLLM produit des **pages wiki lisibles, versionnables et validables** :

```
sources brutes → Ollama → pages Markdown → index FTS5 → API / MCP → agents IA
```

---

## Fonctionnalités

- **Ingestion** — transforme du texte brut en page wiki Markdown via Ollama
- **Recherche** — SQLite FTS5, recherche dans titre, contenu et tags
- **API REST** — lecture, recherche, ingestion, réponse en mode strict
- **Serveur MCP** — les agents IA (Claude Code, Claude Desktop, n8n) consultent le wiki directement
- **Modes de réponse** — `strict`, `validated_only`, `draft`, `source_only`
- **Docker** — démarrage en une commande

---

## Prérequis

- Docker + Docker Compose
- [Ollama](https://ollama.com) installé et lancé sur le host avec un modèle disponible (ex: `mistral`)

```bash
ollama pull mistral
```

---

## Installation

```bash
git clone https://github.com/Nohame/Open-Wiki-LLM.git
cd Open-Wiki-LLM
cp .env.example .env
```

Édite `.env` si besoin (port, modèle Ollama, clé API) :

```env
OLLAMA_MODEL=mistral
API_KEY=              # laisser vide pour désactiver l'auth
APP_PORT=8088
```

---

## Démarrage

```bash
./docker.sh start     # démarre l'API
./docker.sh stop      # arrête
./docker.sh restart   # redémarre
./docker.sh ssh       # shell dans le conteneur
```

Vérification :

```bash
curl http://localhost:8088/health
# {"status":"ok","version":"0.1.0"}
```

---

## Utilisation

### Ajouter une source et ingérer

```bash
curl -X POST http://localhost:8088/api/ingest/text \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <ta_cle>" \
  -d '{
    "text": "La livraison est garantie en 24h sur tout le territoire.",
    "title": "Livraison 24h",
    "tags": ["livraison", "logistique"]
  }'
```

La page est créée dans `wiki/imports/` et la source brute dans `raw/imports/`.

### Reconstruire l'index de recherche

```bash
curl -X POST http://localhost:8088/api/index/rebuild \
  -H "X-API-Key: <ta_cle>"
# {"indexed": 3}
```

### Rechercher

```bash
curl -X POST http://localhost:8088/api/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <ta_cle>" \
  -d '{"q": "livraison", "limit": 5}'
```

### Obtenir une réponse depuis le wiki

```bash
curl -X POST http://localhost:8088/api/answer \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <ta_cle>" \
  -d '{
    "question": "Quel est le délai de livraison ?",
    "mode": "validated_only"
  }'
```

Modes disponibles :

| Mode | Comportement |
|---|---|
| `validated_only` | Répond uniquement depuis les pages `status: validated` |
| `strict` | Idem — retourne un fallback si aucune page validée ne correspond |
| `draft` | Inclut les pages en cours de rédaction |
| `source_only` | Répond depuis les sources brutes uniquement |

### Lire les pages

```bash
# Liste toutes les pages
curl http://localhost:8088/api/pages -H "X-API-Key: <ta_cle>"

# Lire une page par son slug
curl http://localhost:8088/api/pages/imports--livraison-24h -H "X-API-Key: <ta_cle>"
```

---

## Serveur MCP

Le serveur MCP est accessible sur `/mcp` (même port que l'API).

### Claude Code / Claude Desktop

Ajoute dans ta config MCP :

```json
{
  "openwikillm": {
    "type": "http",
    "url": "http://localhost:8088/mcp"
  }
}
```

### n8n (Docker)

Utilise `host.docker.internal` à la place de `localhost` :

```
http://host.docker.internal:8088/api/answer
```

### Outils MCP disponibles

| Outil | Description |
|---|---|
| `wiki_search` | Recherche dans le wiki |
| `wiki_read_page` | Lit le contenu d'une page par slug |
| `wiki_list_pages` | Liste toutes les pages (sans contenu) |
| `wiki_rebuild_index` | Reconstruit l'index FTS5 |

---

## Format des pages wiki

Les pages sont des fichiers Markdown avec frontmatter YAML dans `wiki/` :

```markdown
---
title: Livraison 24h
type: concept
status: validated
confidence: high
sources:
  - raw/imports/livraison-24h.md
updated_at: 2026-05-12
tags:
  - livraison
  - logistique
---

# Livraison 24h

## Résumé

## Règles connues

## Points à confirmer
```

Les pages peuvent être éditées manuellement, versionnées avec Git et validées en changeant `status: draft` → `status: validated`.

---

## Scripts utilitaires

```bash
# Ingestion en masse depuis raw/
python scripts/bulk_ingest.py --raw-dir ./raw/imports

# Audit qualité des pages wiki
python scripts/audit_wiki.py --only-issues

# Évaluation des réponses sur un golden dataset
python scripts/eval_answers.py --dataset evals/golden_dataset.yaml

# Bump de version
./scripts/bump.sh
```

---

## Structure du projet

```
├── backend/          API FastAPI + serveur MCP
├── wiki/             Pages Markdown (éditables manuellement)
├── raw/              Sources brutes (jamais modifiées)
├── data/             Base SQLite (index FTS5)
├── evals/            Golden dataset pour tests de qualité
├── scripts/          Utilitaires CLI
├── docs/             Documentation technique
├── docker-compose.yml
├── docker.sh
└── .env.example
```

---

## Limites connues (v0.1.0)

- Le serveur MCP sur `/mcp` ne vérifie pas le header `X-API-Key`
- Pas de frontend (prévu dans une version future)
- L'ingestion via Ollama peut être lente selon le modèle et la longueur du texte
- La recherche FTS5 est en OR sur les tokens — pas de recherche sémantique (pas de vecteurs)

---

## Stack technique

- **Backend** : Python 3.11, FastAPI, FastMCP 3.x
- **Recherche** : SQLite FTS5
- **LLM** : Ollama (modèle configurable via `OLLAMA_MODEL`)
- **Stockage** : fichiers Markdown + frontmatter YAML
- **Infrastructure** : Docker Compose
