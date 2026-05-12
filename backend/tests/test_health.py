import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends
from app.main import app
from app.core.config import settings
from app.core.auth import verify_api_key


@pytest.fixture
def client():
    return TestClient(app)


def test_health_no_auth_when_key_empty(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_health_with_valid_key(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret")
    response = client.get("/health", headers={"X-API-Key": "secret"})
    assert response.status_code == 200


def test_health_accessible_without_auth_dependency():
    """Health route has no auth dependency — this documents that explicitly."""
    from app.api.health import router
    for route in router.routes:
        assert not route.dependencies, f"Health route should have no dependencies, found: {route.dependencies}"


def test_verify_api_key_rejects_bad_key(monkeypatch):
    """verify_api_key raises 401 when key is set and header doesn't match."""
    monkeypatch.setattr(settings, "api_key", "secret")

    protected_app = FastAPI()

    @protected_app.get("/protected", dependencies=[Depends(verify_api_key)])
    def protected():
        return {"ok": True}

    test_client = TestClient(protected_app)

    response = test_client.get("/protected", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401

    response = test_client.get("/protected")
    assert response.status_code == 401

    response = test_client.get("/protected", headers={"X-API-Key": "secret"})
    assert response.status_code == 200
