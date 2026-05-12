from fastapi import FastAPI
from .api.health import router as health_router
from .api.pages import router as pages_router
from .api.search import router as search_router
from .api.ingest import router as ingest_router
from .api.answer import router as answer_router
from .mcp.server import mcp

app = FastAPI(title="OpenWikiLLM", version="0.1.0")

app.include_router(health_router)
app.include_router(pages_router)
app.include_router(search_router)
app.include_router(ingest_router)
app.include_router(answer_router)
app.mount("/mcp", mcp.http_app())
