import pytest


def test_verify_authorized_email(client):
    response = client.post("/api/verify", json={"email": "authorized@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["eligible"] is True
    assert "verified" in data["message"].lower()
    # Confirm security: No participant names leaked in verify response
    assert "registered_name" not in data
    assert "participants" not in data


def test_verify_case_insensitive_email(client):
    response = client.post("/api/verify", json={"email": "AuThOrized@Example.COM"})
    assert response.status_code == 200
    data = response.json()
    assert data["eligible"] is True


def test_verify_whitespace_email(client):
    response = client.post("/api/verify", json={"email": "   authorized@example.com   "})
    assert response.status_code == 200
    data = response.json()
    assert data["eligible"] is True


def test_verify_unauthorized_email(client):
    response = client.post("/api/verify", json={"email": "random_stranger@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["eligible"] is False
    assert "not eligible" in data["message"].lower()
    assert "participants" not in data  # Never leak participant list


def test_verify_ineligible_email(client):
    response = client.post("/api/verify", json={"email": "ineligible@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["eligible"] is False
    assert "not eligible" in data["message"].lower()


@pytest.mark.parametrize("invalid_email", [
    "",
    "not-an-email",
    "missing_at_domain.com",
    "@nodomain.com",
    "user@.com",
    "user@domain"
])
def test_verify_invalid_email_format(client, invalid_email):
    response = client.post("/api/verify", json={"email": invalid_email})
    assert response.status_code == 422
