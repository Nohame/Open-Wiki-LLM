from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.health import router as health_router
from .api.pages import router as pages_router
from .api.search import router as search_router
from .api.ingest import router as ingest_router
from .api.answer import router as answer_router
from .api.log import router as log_router
from .api.references import router as references_router
from .api.settings import router as settings_router
from .api.connectors import router as connectors_router
from .mcp.server import mcp

_mcp_http = mcp.http_app(transport="streamable-http")
_mcp_sse = mcp.http_app(transport="sse")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    async with _mcp_http.lifespan(app):
        yield


app = FastAPI(title="OpenWikiLLM", version="0.1.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(pages_router)
app.include_router(search_router)
app.include_router(ingest_router)
app.include_router(answer_router)
app.include_router(log_router)
app.include_router(references_router)
app.include_router(settings_router)
app.include_router(connectors_router)

app.mount("/mcp", _mcp_http)      # Streamable HTTP — Claude Code / Claude Desktop
app.mount("/mcp-sse", _mcp_sse)   # SSE legacy — n8n, anciens clients MCP
