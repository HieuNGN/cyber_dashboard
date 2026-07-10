import pytest
from fastapi.testclient import TestClient

from dashboard_config import DashboardConfig, settings_to_config


@pytest.fixture
def client_with_auth(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-secret-key")
    import config
    import main
    import importlib

    importlib.reload(config)
    main.config = settings_to_config(config.Settings())
    from main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client_no_auth(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    import config
    import main
    import importlib

    importlib.reload(config)
    main.config = settings_to_config(config.Settings())
    from main import app
    with TestClient(app) as client:
        yield client


def test_export_requires_api_key(client_with_auth):
    r = client_with_auth.post("/api/export", json={"content": "x"})
    assert r.status_code == 401

    r = client_with_auth.post(
        "/api/export",
        json={"content": "x"},
        headers={"Authorization": "Bearer test-secret-key"},
    )
    assert r.status_code == 200


def test_export_disabled_without_api_key(client_no_auth):
    r = client_no_auth.post(
        "/api/export",
        json={"content": "x"},
        headers={"Authorization": "Bearer anything"},
    )
    assert r.status_code == 403


def test_bookmark_requires_api_key(client_with_auth):
    r = client_with_auth.post("/api/articles/1/bookmark")
    assert r.status_code == 401

    r = client_with_auth.post(
        "/api/articles/1/bookmark",
        headers={"Authorization": "Bearer test-secret-key"},
    )
    # repository is empty, so endpoint returns 500-ish? We only verify auth gate passed.
    assert r.status_code in (200, 404, 500)


def test_read_requires_api_key(client_with_auth):
    r = client_with_auth.post("/api/articles/1/read")
    assert r.status_code == 401

    r = client_with_auth.post(
        "/api/articles/1/read",
        headers={"Authorization": "Bearer test-secret-key"},
    )
    assert r.status_code in (200, 404, 500)


def test_trigger_update_requires_api_key(client_with_auth):
    r = client_with_auth.post("/api/trigger-update")
    assert r.status_code == 401

    r = client_with_auth.post(
        "/api/trigger-update",
        headers={"Authorization": "Bearer test-secret-key"},
    )
    assert r.status_code == 200


def test_openapi_disabled(client_with_auth):
    assert client_with_auth.get("/docs").status_code == 404
    assert client_with_auth.get("/redoc").status_code == 404
    assert client_with_auth.get("/openapi.json").status_code == 404


def test_security_headers_present(client_with_auth):
    r = client_with_auth.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in r.headers


def test_validation_errors_are_generic(client_with_auth):
    r = client_with_auth.post(
        "/api/export",
        content="not json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 422
    assert "error" in r.json()
    assert "validation failed" in r.json()["detail"].lower()
    assert "loc" not in r.json()
    assert "body" not in r.json()


def test_cors_defaults_to_no_origins(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    import config
    import importlib

    importlib.reload(config)
    assert config.settings.cors_origins == ""
    assert config.settings.cors_origins_list == []
