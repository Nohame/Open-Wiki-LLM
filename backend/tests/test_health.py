import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


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


def test_health_route_ignores_auth(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret")
    response = client.get("/health")
    assert response.status_code == 200
