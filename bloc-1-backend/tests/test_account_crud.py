import pytest


@pytest.fixture
def persona_id(client, persona_payload):
    r = client.post("/api/v1/personas", json=persona_payload)
    assert r.status_code == 201
    return r.json()["id"]


@pytest.fixture
def account_payload(persona_id):
    return {
        "persona_id": persona_id,
        "platform": "linkedin",
        "kind": "company_page",
        "page_url": "https://www.linkedin.com/company/noisyless/admin/",
        "identity_name": "Noisyless",
    }


def test_create_account(client, account_payload):
    r = client.post("/api/v1/accounts", json=account_payload)
    assert r.status_code == 201
    data = r.json()
    assert data["platform"] == "linkedin"
    assert data["kind"] == "company_page"
    assert data["identity_name"] == "Noisyless"
    assert data["enabled"] is True


def test_create_account_invalid_platform(client, account_payload):
    r = client.post("/api/v1/accounts", json={**account_payload, "platform": "myspace"})
    assert r.status_code == 422


def test_create_account_invalid_kind(client, account_payload):
    r = client.post("/api/v1/accounts", json={**account_payload, "kind": "fan_club"})
    assert r.status_code == 422


def test_list_accounts_filter_by_persona(client, account_payload, persona_id):
    client.post("/api/v1/accounts", json=account_payload)
    client.post("/api/v1/accounts", json={**account_payload, "platform": "instagram", "kind": "business_account"})

    r = client.get(f"/api/v1/accounts?persona_id={persona_id}")
    assert r.status_code == 200
    assert len(r.json()) == 2

    r2 = client.get("/api/v1/accounts?persona_id=unknown")
    assert r2.json() == []


def test_update_account(client, account_payload):
    account_id = client.post("/api/v1/accounts", json=account_payload).json()["id"]
    r = client.patch(f"/api/v1/accounts/{account_id}", json={"enabled": False, "identity_name": "Noisyless SAS"})
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    assert r.json()["identity_name"] == "Noisyless SAS"


def test_delete_account(client, account_payload):
    account_id = client.post("/api/v1/accounts", json=account_payload).json()["id"]
    assert client.delete(f"/api/v1/accounts/{account_id}").status_code == 204
    assert client.get(f"/api/v1/accounts/{account_id}").status_code == 404


def test_get_account_not_found(client):
    assert client.get("/api/v1/accounts/nope").status_code == 404
