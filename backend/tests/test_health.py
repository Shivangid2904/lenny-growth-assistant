from unittest.mock import patch
import httpx


def test_health_success(client):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.status_code = 200
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "dependencies" in data
        assert data["dependencies"]["database"] == "up"
        assert data["dependencies"]["ollama"] == "up"
        assert data["dependencies"]["claude_api"] in ("configured", "not_configured")


def test_health_ollama_unreachable(client):
    with patch("httpx.get", side_effect=httpx.ConnectError("Connection refused")):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["dependencies"]["database"] == "up"
        assert data["dependencies"]["ollama"] == "down"


def test_health_claude_not_called(client):
    """Verify health endpoint does not make live external Claude API calls."""
    with patch("httpx.get") as mock_get:
        mock_get.return_value.status_code = 200
        response = client.get("/health")
        assert response.status_code == 200
        # Only ollama was probed via httpx
        assert mock_get.call_count == 1
        assert "api.anthropic.com" not in str(mock_get.call_args)
