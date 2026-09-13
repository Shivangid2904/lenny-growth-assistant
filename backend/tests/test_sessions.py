import uuid


def test_create_session(client):
    response = client.post("/api/sessions", json={"title": "Test Session"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Session"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_session_without_title(client):
    response = client.post("/api/sessions", json={})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] is None
    assert "id" in data


def test_list_sessions(client):
    client.post("/api/sessions", json={"title": "Session 1"})
    client.post("/api/sessions", json={"title": "Session 2"})

    response = client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    titles = [s["title"] for s in data]
    assert "Session 1" in titles
    assert "Session 2" in titles


def test_get_session(client):
    create_res = client.post("/api/sessions", json={"title": "Specific Session"})
    session_id = create_res.json()["id"]

    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["title"] == "Specific Session"
    assert "messages" in data
    assert data["messages"] == []


def test_missing_session_returns_structured_not_found(client):
    non_existent_id = uuid.uuid4()
    response = client.get(f"/api/sessions/{non_existent_id}")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "SESSION_NOT_FOUND"
    assert "not found" in data["error"]["message"].lower()


def test_delete_session(client):
    create_res = client.post("/api/sessions", json={"title": "To Delete"})
    session_id = create_res.json()["id"]

    del_res = client.delete(f"/api/sessions/{session_id}")
    assert del_res.status_code == 204

    # Verify session is gone
    get_res = client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 404
    assert get_res.json()["error"]["code"] == "SESSION_NOT_FOUND"


def test_delete_missing_session_returns_structured_error(client):
    non_existent_id = uuid.uuid4()
    response = client.delete(f"/api/sessions/{non_existent_id}")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "SESSION_NOT_FOUND"


def test_validation_error_returns_structured_error(client):
    # Pass invalid UUID in URL path
    response = client.get("/api/sessions/invalid-uuid-1234")
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_FAILED"
