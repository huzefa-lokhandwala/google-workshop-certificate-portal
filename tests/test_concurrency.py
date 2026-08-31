import concurrent.futures
from fastapi.testclient import TestClient
from backend.app.main import app, rate_limiter
from backend.app.database import get_db
from backend.app.services.participant_service import upsert_participant


def test_concurrent_duplicate_generation_race_condition(db_session):
    # Seed a fresh participant
    upsert_participant(db_session, "race_test@example.com", name="Race Runner", eligible=True)
    rate_limiter.requests.clear()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    def make_request():
        return client.post(
            "/api/certificates/generate",
            json={"name": "Race Runner", "email": "race_test@example.com"}
        )

    # Launch 5 concurrent generation attempts for the exact same participant
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request) for _ in range(5)]
        responses = [f.result() for f in futures]

    status_codes = [r.status_code for r in responses]
    print("Concurrent status codes:", status_codes)

    # Exactly 1 request MUST succeed with 200, all other concurrent attempts MUST be blocked with 409
    assert status_codes.count(200) == 1
    assert status_codes.count(409) == 4

    app.dependency_overrides.clear()
