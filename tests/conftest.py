import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app, rate_limiter
from backend.app.models import Participant
from backend.app.services.participant_service import upsert_participant

# Use in-memory SQLite database for fast, isolated unit tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Seed standard test data
    upsert_participant(db, "authorized@example.com", name="Alice Wonderland", eligible=True)
    upsert_participant(db, "ineligible@example.com", name="Bob Locked", eligible=False)
    
    # Create already generated participant
    p_gen, _ = upsert_participant(db, "already_generated@example.com", name="Charlie Done", eligible=True)
    p_gen.certificate_generated = True
    db.commit()

    yield db

    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    rate_limiter.requests.clear()  # Reset rate limit counter for test isolation
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
