PLANNING_PAYLOAD = {
    "date_debut": "2026-08-01T00:00:00",
    "date_fin": "2026-08-31T23:59:59",
}

BASE_POST = {
    "platform": "linkedin",
    "angle_editorial": "Comment réduire les nuisances sonores en location courte durée",
    "format": "text_only",
}


def make_persona(client, persona_payload):
    return client.post("/api/v1/personas", json=persona_payload).json()


def make_planning(client, persona_id):
    return client.post("/api/v1/plannings", json={**PLANNING_PAYLOAD, "persona_id": persona_id}).json()


def test_create_post_valid(client, persona_payload):
    persona = make_persona(client, persona_payload)
    planning = make_planning(client, persona["id"])
    payload = {**BASE_POST, "planning_id": planning["id"], "persona_id": persona["id"]}
    response = client.post("/api/v1/posts", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "draft"
    assert data["platform"] == "linkedin"


def test_create_post_invalid_planning(client, persona_payload):
    persona = make_persona(client, persona_payload)
    payload = {**BASE_POST, "planning_id": "nonexistent", "persona_id": persona["id"]}
    response = client.post("/api/v1/posts", json=payload)
    assert response.status_code == 404


def test_create_post_invalid_persona(client, persona_payload):
    persona = make_persona(client, persona_payload)
    planning = make_planning(client, persona["id"])
    payload = {**BASE_POST, "planning_id": planning["id"], "persona_id": "nonexistent"}
    response = client.post("/api/v1/posts", json=payload)
    assert response.status_code == 404


def test_create_post_missing_fields(client):
    response = client.post("/api/v1/posts", json={"platform": "linkedin"})
    assert response.status_code == 422


def test_create_post_invalid_platform(client, persona_payload):
    persona = make_persona(client, persona_payload)
    planning = make_planning(client, persona["id"])
    payload = {**BASE_POST, "planning_id": planning["id"], "persona_id": persona["id"], "platform": "twitter"}
    response = client.post("/api/v1/posts", json=payload)
    assert response.status_code == 422


def test_list_posts_empty(client):
    response = client.get("/api/v1/posts")
    assert response.status_code == 200
    assert response.json() == []


def test_list_posts_after_creation(client, persona_payload):
    persona = make_persona(client, persona_payload)
    planning = make_planning(client, persona["id"])
    client.post("/api/v1/posts", json={**BASE_POST, "planning_id": planning["id"], "persona_id": persona["id"]})
    response = client.get("/api/v1/posts")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_post_by_id(client, persona_payload):
    persona = make_persona(client, persona_payload)
    planning = make_planning(client, persona["id"])
    created = client.post("/api/v1/posts", json={**BASE_POST, "planning_id": planning["id"], "persona_id": persona["id"]}).json()
    response = client.get(f"/api/v1/posts/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_post_not_found(client):
    response = client.get("/api/v1/posts/nonexistent")
    assert response.status_code == 404


def test_update_post_status(client, persona_payload):
    persona = make_persona(client, persona_payload)
    planning = make_planning(client, persona["id"])
    created = client.post("/api/v1/posts", json={**BASE_POST, "planning_id": planning["id"], "persona_id": persona["id"]}).json()
    response = client.patch(f"/api/v1/posts/{created['id']}", json={"status": "validated"})
    assert response.status_code == 200
    assert response.json()["status"] == "validated"


def test_update_post_text(client, persona_payload):
    persona = make_persona(client, persona_payload)
    planning = make_planning(client, persona["id"])
    created = client.post("/api/v1/posts", json={**BASE_POST, "planning_id": planning["id"], "persona_id": persona["id"]}).json()
    response = client.patch(f"/api/v1/posts/{created['id']}", json={"text": "Mon super post LinkedIn", "image_url": "https://example.com/img.png"})
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "Mon super post LinkedIn"
    assert data["image_url"] == "https://example.com/img.png"


def test_delete_post(client, persona_payload):
    persona = make_persona(client, persona_payload)
    planning = make_planning(client, persona["id"])
    created = client.post("/api/v1/posts", json={**BASE_POST, "planning_id": planning["id"], "persona_id": persona["id"]}).json()
    response = client.delete(f"/api/v1/posts/{created['id']}")
    assert response.status_code == 204

    response = client.get(f"/api/v1/posts/{created['id']}")
    assert response.status_code == 404


def test_filter_posts_by_status(client, persona_payload):
    persona = make_persona(client, persona_payload)
    planning = make_planning(client, persona["id"])
    post = client.post("/api/v1/posts", json={**BASE_POST, "planning_id": planning["id"], "persona_id": persona["id"]}).json()
    client.patch(f"/api/v1/posts/{post['id']}", json={"status": "validated"})

    response = client.get("/api/v1/posts?status=validated")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "validated"

    response = client.get("/api/v1/posts?status=draft")
    assert response.status_code == 200
    assert response.json() == []


def test_filter_posts_by_platform(client, persona_payload):
    persona = make_persona(client, persona_payload)
    planning = make_planning(client, persona["id"])
    client.post("/api/v1/posts", json={**BASE_POST, "planning_id": planning["id"], "persona_id": persona["id"], "platform": "linkedin"})
    client.post("/api/v1/posts", json={**BASE_POST, "planning_id": planning["id"], "persona_id": persona["id"], "platform": "instagram"})

    response = client.get("/api/v1/posts?platform=linkedin")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["platform"] == "linkedin"


def test_filter_posts_by_persona_id(client, persona_payload):
    persona1 = make_persona(client, persona_payload)
    persona2 = client.post("/api/v1/personas", json={**persona_payload, "bu": "afluxo", "nom": "Autre persona"}).json()
    planning1 = make_planning(client, persona1["id"])
    planning2 = make_planning(client, persona2["id"])

    client.post("/api/v1/posts", json={**BASE_POST, "planning_id": planning1["id"], "persona_id": persona1["id"]})
    client.post("/api/v1/posts", json={**BASE_POST, "planning_id": planning2["id"], "persona_id": persona2["id"]})

    response = client.get(f"/api/v1/posts?persona_id={persona1['id']}")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_filter_posts_by_planning_id(client, persona_payload):
    persona = make_persona(client, persona_payload)
    planning1 = make_planning(client, persona["id"])
    planning2 = make_planning(client, persona["id"])

    client.post("/api/v1/posts", json={**BASE_POST, "planning_id": planning1["id"], "persona_id": persona["id"]})
    client.post("/api/v1/posts", json={**BASE_POST, "planning_id": planning2["id"], "persona_id": persona["id"]})

    response = client.get(f"/api/v1/posts?planning_id={planning1['id']}")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_cascade_delete_planning_removes_posts(client, persona_payload):
    persona = make_persona(client, persona_payload)
    planning = make_planning(client, persona["id"])
    post = client.post("/api/v1/posts", json={**BASE_POST, "planning_id": planning["id"], "persona_id": persona["id"]}).json()

    client.delete(f"/api/v1/plannings/{planning['id']}")

    response = client.get(f"/api/v1/posts/{post['id']}")
    assert response.status_code == 404


def test_cascade_delete_persona_removes_posts(client, persona_payload):
    persona = make_persona(client, persona_payload)
    planning = make_planning(client, persona["id"])
    post = client.post("/api/v1/posts", json={**BASE_POST, "planning_id": planning["id"], "persona_id": persona["id"]}).json()

    client.delete(f"/api/v1/personas/{persona['id']}")

    response = client.get(f"/api/v1/posts/{post['id']}")
    assert response.status_code == 404
