import io
import pytest
from pypdf import PdfReader
from backend.app.config import get_settings


def test_generate_certificate_authorized_success(client, db_session):
    response = client.post(
        "/api/certificates/generate",
        json={"name": "Alice Wonderland", "email": "authorized@example.com"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "Certificate_Alice_Wonderland.pdf" in response.headers["content-disposition"]

    # Verify PDF content
    pdf_bytes = response.content
    assert pdf_bytes.startswith(b"%PDF-")

    # Read PDF text with pypdf
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == 1
    page_text = reader.pages[0].extract_text()
    assert "Alice Wonderland" in page_text

    # Verify participant model is updated
    from backend.app.services.participant_service import get_participant_by_email
    p = get_participant_by_email(db_session, "authorized@example.com")
    assert p.certificate_generated is True
    assert p.generated_at is not None


@pytest.mark.parametrize("test_name", [
    "Ali",
    "John Doe",
    "Demo Participant",
    "A Very Long Participant Name For Testing",
    "Rahul Sharma",
    "Priya Patel"
])
def test_generate_certificate_various_name_lengths(client, test_name, monkeypatch):
    # Allow regeneration for testing various names on same account
    settings = get_settings()
    monkeypatch.setattr(settings, "ALLOW_CERTIFICATE_REGENERATION", True)

    response = client.post(
        "/api/certificates/generate",
        json={"name": test_name, "email": "authorized@example.com"}
    )
    assert response.status_code == 200
    pdf_bytes = response.content
    assert pdf_bytes.startswith(b"%PDF-")

    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == 1
    page = reader.pages[0]
    # Check page dimensions match actual template (884.38 x 637.78 pt)
    assert round(float(page.mediabox.width), 1) == 884.4
    assert round(float(page.mediabox.height), 1) == 637.8
    assert test_name in page.extract_text()


def test_generate_certificate_unauthorized_fails(client):
    response = client.post(
        "/api/certificates/generate",
        json={"name": "Hacker Person", "email": "unauthorized@example.com"}
    )
    assert response.status_code == 403
    assert "not eligible" in response.json()["detail"].lower()


def test_generate_certificate_ineligible_fails(client):
    response = client.post(
        "/api/certificates/generate",
        json={"name": "Bob Locked", "email": "ineligible@example.com"}
    )
    assert response.status_code == 403
    assert "not eligible" in response.json()["detail"].lower()


@pytest.mark.parametrize("invalid_name", [
    "",
    " ",
    "A",  # Too short (min 2 chars)
    "A" * 105,  # Too long (max 100 chars)
    "<script>alert(1)</script>",  # Malicious tags
    "Name with \n newline",
])
def test_generate_certificate_invalid_name(client, invalid_name):
    response = client.post(
        "/api/certificates/generate",
        json={"name": invalid_name, "email": "authorized@example.com"}
    )
    assert response.status_code == 422


def test_duplicate_generation_blocked_by_default(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ALLOW_CERTIFICATE_REGENERATION", False)

    response = client.post(
        "/api/certificates/generate",
        json={"name": "Charlie Done", "email": "already_generated@example.com"}
    )
    assert response.status_code == 409
    assert "already been generated" in response.json()["detail"].lower()


def test_duplicate_generation_allowed_when_configured(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ALLOW_CERTIFICATE_REGENERATION", True)

    response = client.post(
        "/api/certificates/generate",
        json={"name": "Charlie Done", "email": "already_generated@example.com"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_missing_template_error_handling(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "CERTIFICATE_TEMPLATE_PATH", "backend/templates/non_existent.pdf")

    response = client.post(
        "/api/certificates/generate",
        json={"name": "Alice Wonderland", "email": "authorized@example.com"}
    )
    assert response.status_code == 500
    assert "non_existent.pdf" not in response.text
    assert "Something went wrong" in response.json()["detail"]
