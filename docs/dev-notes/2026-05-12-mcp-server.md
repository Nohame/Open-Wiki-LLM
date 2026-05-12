# MCP Server — Montage dans FastAPI

## Objectif
Exposer les outils wiki (lecture, recherche, indexation) via le protocole MCP
pour permettre aux agents IA (Claude Code, Claude Desktop) de consulter le wiki.

## Fichiers modifiés
- `backend/app/mcp/server.py` (créé)
- `backend/app/main.py` (montage `/mcp`)

## Décisions prises
- FastMCP monté via ASGI sur `/mcp` — même process que FastAPI
- Auth couverte par le middleware FastAPI (X-API-Key)
- FastMCP 3.2.4 : `mcp.http_app()` remplace `mcp.get_asgi_app()` (API v2 obsolète)

## Config client MCP
```json
{
  "openwikillm": {
    "type": "http",
    "url": "http://localhost:8088/mcp"
  }
}
```

## Tests effectués
- wiki_list_pages, wiki_read_page, wiki_search, wiki_rebuild_index

## Prochaines étapes
- Étape 5 : ingestion texte via Ollama
