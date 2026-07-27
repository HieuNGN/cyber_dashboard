import pytest
from fastapi.testclient import TestClient


def test_export_requires_api_key(client_with_auth):
    r = client_with_auth.post("/api/export", json={"content": "x"})
    assert r.status_code == 401

    r = client_with_auth.post(
        "/api/export",
        json={"content": "x"},
        headers={"Authorization": "Bearer test-secret-key"},
    )
    assert r.status_code == 200


def test_wrong_api_key_returns_401(client_with_auth):
    r = client_with_auth.post(
        "/api/export",
        json={"content": "x"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert r.status_code == 401


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


def test_cors_methods_and_headers_are_explicit(client_with_auth):
    r = client_with_auth.options(
        "/api/news",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    # Empty allow_origins => no ACAO header, but middleware still processes preflight.
    # We assert the configured allowlist is reflected when origin is allowed.
    assert r.status_code in (200, 400)
    # Disallowed method should not be claimed allowed.
    r2 = client_with_auth.options(
        "/api/news",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert r2.headers.get("access-control-allow-methods", "") != "*"
    assert r2.headers.get("access-control-allow-headers", "") != "*"


def test_cache_control_no_store(client_with_auth):
    r = client_with_auth.get("/health")
    assert r.headers.get("Cache-Control") == "no-store"


def test_sse_rejects_when_cap_reached(client_with_auth):
    from main import app
    # ponytail: test the cap logic directly via app.state — StreamingResponse
    # + TestClient make real-stream assertions awkward; the gate is the counter.
    app.state.sse_client_count = 20
    try:
        r = client_with_auth.get("/api/events")
        assert r.status_code == 503
        assert "Too many SSE connections" in r.json()["error"]
    finally:
        app.state.sse_client_count = 0


def test_export_rejects_oversized_content(client_with_auth):
    big = "x" * 200_001
    r = client_with_auth.post(
        "/api/export",
        json={"content": big},
        headers={"Authorization": "Bearer test-secret-key"},
    )
    assert r.status_code == 422
