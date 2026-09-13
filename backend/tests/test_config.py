def test_config_endpoint(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "active_provider" in data
    assert "cloud_model" in data
    assert "local_model" in data
    assert "embedding_model" in data


def test_config_does_not_expose_secrets(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    # Ensure no secret keys or database connection strings are present
    response_text = response.text.lower()
    assert "api_key" not in response_text
    assert "secret" not in response_text
    assert "password" not in response_text
    assert "postgres" not in response_text
    assert "database_url" not in data
    assert "anthropic_api_key" not in data
