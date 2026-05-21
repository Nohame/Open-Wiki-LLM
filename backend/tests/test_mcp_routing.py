from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_mcp_streamable_http_mount_exists():
    """Streamable HTTP MCP endpoint doit rester monté sur /mcp."""
    mount_paths = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/mcp" in mount_paths


def test_mcp_sse_mount_exists():
    """SSE MCP endpoint doit être monté sur /mcp-sse pour les clients legacy (n8n)."""
    mount_paths = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/mcp-sse" in mount_paths


def test_mcp_both_transports_distinct():
    """Les deux mounts doivent pointer vers des apps distinctes (transports différents)."""
    mounts = {r.path: r for r in app.routes if hasattr(r, "path") and r.path in ("/mcp", "/mcp-sse")}
    assert len(mounts) == 2
    assert mounts["/mcp"].app is not mounts["/mcp-sse"].app
