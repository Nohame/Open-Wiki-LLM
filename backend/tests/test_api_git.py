import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "")
    return TestClient(app)


def test_git_status_not_initialized(client):
    with patch("app.api.git.git_service.get_status") as mock:
        mock.return_value = {
            "enabled": False,
            "initialized": False,
            "last_commit": None,
            "dirty_files": 0,
        }
        response = client.get("/api/git/status")
    assert response.status_code == 200
    data = response.json()
    assert data["initialized"] is False
    assert data["enabled"] is False


def test_git_status_initialized(client):
    with patch("app.api.git.git_service.get_status") as mock:
        mock.return_value = {
            "enabled": True,
            "initialized": True,
            "last_commit": "abc1234 chore(wiki): init 2026-06-02",
            "dirty_files": 0,
        }
        response = client.get("/api/git/status")
    assert response.status_code == 200
    assert response.json()["initialized"] is True
    assert response.json()["last_commit"] is not None


def test_git_init_when_not_initialized(client):
    with patch("app.api.git.git_service.is_initialized", return_value=False), \
         patch("app.api.git.git_service.init_repo") as mock_init:
        response = client.post("/api/git/init")
    assert response.status_code == 200
    assert response.json()["status"] == "initialized"
    mock_init.assert_called_once()


def test_git_init_already_initialized(client):
    with patch("app.api.git.git_service.is_initialized", return_value=True), \
         patch("app.api.git.git_service.init_repo") as mock_init:
        response = client.post("/api/git/init")
    assert response.status_code == 200
    assert response.json()["status"] == "already_initialized"
    mock_init.assert_not_called()


def test_git_push(client):
    with patch("app.api.git.git_service.push") as mock_push:
        response = client.post("/api/git/push")
    assert response.status_code == 200
    assert response.json()["status"] == "push_triggered"
    mock_push.assert_called_once()


def test_git_log(client):
    with patch("app.api.git.git_service.get_log") as mock_log:
        mock_log.return_value = [
            {"hash": "abc1234", "message": "chore(wiki): init", "date": "2026-06-02 10:00:00 +0200"}
        ]
        response = client.get("/api/git/log")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["hash"] == "abc1234"
    assert data[0]["message"] == "chore(wiki): init"


def test_git_log_empty(client):
    with patch("app.api.git.git_service.get_log", return_value=[]):
        response = client.get("/api/git/log")
    assert response.status_code == 200
    assert response.json() == []


def test_git_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret")
    client = TestClient(app)
    response = client.get("/api/git/status")
    assert response.status_code == 401
