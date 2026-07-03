def test_create_persona_valid(client, persona_payload):
    response = client.post("/api/v1/personas", json=persona_payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["bu"] == "noisyless"
    assert data["nom"] == persona_payload["nom"]
    assert "created_at" in data
    assert "updated_at" in data


def test_create_persona_invalid_missing_fields(client):
    response = client.post("/api/v1/personas", json={"bu": "noisyless"})
    assert response.status_code == 422


def test_create_persona_invalid_bu(client, persona_payload):
    payload = {**persona_payload, "bu": "unknown_bu"}
    response = client.post("/api/v1/personas", json=payload)
    assert response.status_code == 422


def test_list_personas_empty(client):
    response = client.get("/api/v1/personas")
    assert response.status_code == 200
    assert response.json() == []


def test_list_personas_after_creation(client, persona_payload):
    client.post("/api/v1/personas", json=persona_payload)
    response = client.get("/api/v1/personas")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["bu"] == "noisyless"


def test_get_persona_by_id(client, persona_payload):
    created = client.post("/api/v1/personas", json=persona_payload).json()
    response = client.get(f"/api/v1/personas/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_persona_not_found(client):
    response = client.get("/api/v1/personas/nonexistent-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_persona_partial(client, persona_payload):
    created = client.post("/api/v1/personas", json=persona_payload).json()
    response = client.patch(
        f"/api/v1/personas/{created['id']}",
        json={"nom": "Nouveau nom du persona"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nom"] == "Nouveau nom du persona"
    assert data["bu"] == "noisyless"


def test_delete_persona(client, persona_payload):
    created = client.post("/api/v1/personas", json=persona_payload).json()
    response = client.delete(f"/api/v1/personas/{created['id']}")
    assert response.status_code == 204

    response = client.get(f"/api/v1/personas/{created['id']}")
    assert response.status_code == 404


def test_delete_persona_not_found(client):
    response = client.delete("/api/v1/personas/nonexistent-id")
    assert response.status_code == 404


def test_list_personas_pagination(client, persona_payload):
    for i in range(3):
        payload = {**persona_payload, "nom": f"Persona {i}"}
        client.post("/api/v1/personas", json=payload)

    response = client.get("/api/v1/personas?skip=1&limit=1")
    assert response.status_code == 200
    assert len(response.json()) == 1
