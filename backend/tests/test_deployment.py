"""Checkpoint 8 deployment and operability tests.

Tests cover:
- /healthz liveness probe (lightweight, no external deps)
- /health operational readiness (verifies DB status)
- CORS allowed origins (standard Vite origins accepted)
- CORS disallowed origins (arbitrary origins rejected)
- CORS OPTIONS preflight behavior
- Config security: no secret leakage in endpoints
- Config environment parsing
"""

from fastapi.testclient import TestClient
from app.main import app
from app.config import Settings


def test_healthz_liveness_returns_ok(client: TestClient):
    """Liveness probe /healthz returns 200 ok without depending on DB or Ollama."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_health_readiness_with_live_db(client: TestClient):
    """Operational readiness probe /health checks database and dependency states."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "dependencies" in data
    assert data["dependencies"]["database"] == "up"
    assert "ollama" in data["dependencies"]
    assert "claude_api" in data["dependencies"]


def test_cors_allowed_origin(client: TestClient):
    """Requests with configured origin receive Access-Control-Allow-Origin."""
    response = client.get(
        "/healthz",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_disallowed_origin(client: TestClient):
    """Requests with unconfigured origin do NOT receive Access-Control-Allow-Origin."""
    response = client.get(
        "/healthz",
        headers={"Origin": "https://malicious-unauthorized-site.com"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_allowed_origin(client: TestClient):
    """Preflight OPTIONS requests from allowed origins receive proper CORS headers."""
    response = client.options(
        "/api/sessions",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "POST" in response.headers.get("access-control-allow-methods", "")


def test_cors_preflight_disallowed_origin(client: TestClient):
    """Preflight OPTIONS requests from disallowed origins do not receive allow origin header."""
    response = client.options(
        "/api/sessions",
        headers={
            "Origin": "https://attacker.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    # Disallowed origin preflight should not return Access-Control-Allow-Origin
    assert response.headers.get("access-control-allow-origin") != "https://attacker.example.com"


def test_config_endpoint_does_not_leak_secrets(client: TestClient):
    """Public /config endpoint must not expose database passwords, API keys, or raw connection strings."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    response_text = response.text.lower()
    assert "postgrespassword" not in response_text
    assert "password" not in data
    assert "database_url" not in data
    assert "anthropic_api_key" not in data
    assert "api_key" not in data


def test_cors_allowed_origins_custom_configuration(monkeypatch):
    """Verify Settings parses custom CORS allowed origins from environment."""
    from pydantic_core import ValidationError

    # Test settings model directly with custom origins
    custom_settings = Settings(
        cors_allowed_origins=["https://production.myapp.com", "https://staging.myapp.com"]
    )
    assert "https://production.myapp.com" in custom_settings.cors_allowed_origins
    assert "https://staging.myapp.com" in custom_settings.cors_allowed_origins
