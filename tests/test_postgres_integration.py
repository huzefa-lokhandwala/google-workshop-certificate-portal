import os
import io
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.database import Base, get_db
from backend.app.main import app, rate_limiter
from backend.app.models import Participant
from backend.app.services.participant_service import (
    upsert_participant,
    get_participant_by_email,
    claim_certificate_generation
)

PG_TEST_URL = os.getenv("PG_TEST_URL", "postgresql://127.0.0.1:5432/cert_test_db")


def is_postgres_available():
    try:
        engine = create_engine(PG_TEST_URL, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.mark.skipif(not is_postgres_available(), reason="PostgreSQL is not available")
class TestPostgresIntegration:

    @pytest.fixture(autouse=True)
    def setup_pg_db(self):
        rate_limiter.requests.clear()
        engine = create_engine(PG_TEST_URL, pool_pre_ping=True)
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        Session = sessionmaker(bind=engine)
        self.session = Session()

        # Seed initial test records
        upsert_participant(self.session, "pg_user@example.com", name="PG User", eligible=True)
        upsert_participant(self.session, "pg_ineligible@example.com", name="PG Ineligible", eligible=False)

        def override_get_db():
            db = Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        yield

        app.dependency_overrides.clear()
        self.session.close()
        Base.metadata.drop_all(bind=engine)

    def test_pg_connection_and_table_structure(self):
        assert self.session is not None
        p = get_participant_by_email(self.session, "pg_user@example.com")
        assert p is not None
        assert p.normalized_email == "pg_user@example.com"
        assert p.eligible is True
        assert p.certificate_generated is False

    def test_pg_verify_endpoint(self):
        # Case insensitivity and whitespace on Postgres
        resp = self.client.post("/api/verify", json={"email": "  PG_User@example.COM  "})
        assert resp.status_code == 200
        data = resp.json()
        assert data["eligible"] is True
        assert "verified" in data["message"].lower()
        # Verify no names or IDs are leaked in verification response
        assert "registered_name" not in data

    def test_pg_atomic_claim_and_certificate_generation(self):
        resp = self.client.post(
            "/api/certificates/generate",
            json={"name": "PG User", "email": "pg_user@example.com"}
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF-")

        # Verify DB is updated on PostgreSQL
        p = get_participant_by_email(self.session, "pg_user@example.com")
        assert p.certificate_generated is True
        assert p.generated_at is not None

        # Verify duplicate generation attempt returns 409 Conflict
        dup_resp = self.client.post(
            "/api/certificates/generate",
            json={"name": "PG User", "email": "pg_user@example.com"}
        )
        assert dup_resp.status_code == 409
        assert "already been generated" in dup_resp.json()["detail"].lower()
