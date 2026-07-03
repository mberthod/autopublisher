PLANNING_PAYLOAD = {
    "date_debut": "2026-08-01T00:00:00",
    "date_fin": "2026-08-31T23:59:59",
}


def make_persona(client, persona_payload):
    return client.post("/api/v1/personas", json=persona_payload).json()


def test_create_planning_valid(client, persona_payload):
    persona = make_persona(client, persona_payload)
    payload = {**PLANNING_PAYLOAD, "persona_id": persona["id"]}
    response = client.post("/api/v1/plannings", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["persona_id"] == persona["id"]


def test_create_planning_invalid_persona(client):
    payload = {**PLANNING_PAYLOAD, "persona_id": "nonexistent"}
    response = client.post("/api/v1/plannings", json=payload)
    assert response.status_code == 404


def test_create_planning_missing_fields(client):
    response = client.post("/api/v1/plannings", json={"persona_id": "some-id"})
    assert response.status_code == 422


def test_list_plannings_empty(client):
    response = client.get("/api/v1/plannings")
    assert response.status_code == 200
    assert response.json() == []


def test_list_plannings_after_creation(client, persona_payload):
    persona = make_persona(client, persona_payload)
    client.post("/api/v1/plannings", json={**PLANNING_PAYLOAD, "persona_id": persona["id"]})
    response = client.get("/api/v1/plannings")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_planning_by_id_with_posts(client, persona_payload):
    persona = make_persona(client, persona_payload)
    created = client.post("/api/v1/plannings", json={**PLANNING_PAYLOAD, "persona_id": persona["id"]}).json()
    response = client.get(f"/api/v1/plannings/{created['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created["id"]
    assert "posts" in data
    assert data["posts"] == []


def test_get_planning_not_found(client):
    response = client.get("/api/v1/plannings/nonexistent")
    assert response.status_code == 404


def test_update_planning(client, persona_payload):
    persona = make_persona(client, persona_payload)
    created = client.post("/api/v1/plannings", json={**PLANNING_PAYLOAD, "persona_id": persona["id"]}).json()
    response = client.patch(
        f"/api/v1/plannings/{created['id']}",
        json={"date_fin": "2026-09-30T23:59:59"},
    )
    assert response.status_code == 200
    assert "2026-09-30" in response.json()["date_fin"]


def test_delete_planning(client, persona_payload):
    persona = make_persona(client, persona_payload)
    created = client.post("/api/v1/plannings", json={**PLANNING_PAYLOAD, "persona_id": persona["id"]}).json()
    response = client.delete(f"/api/v1/plannings/{created['id']}")
    assert response.status_code == 204

    response = client.get(f"/api/v1/plannings/{created['id']}")
    assert response.status_code == 404


def test_cascade_delete_persona_removes_plannings(client, persona_payload):
    persona = make_persona(client, persona_payload)
    planning = client.post("/api/v1/plannings", json={**PLANNING_PAYLOAD, "persona_id": persona["id"]}).json()

    client.delete(f"/api/v1/personas/{persona['id']}")

    response = client.get(f"/api/v1/plannings/{planning['id']}")
    assert response.status_code == 404
