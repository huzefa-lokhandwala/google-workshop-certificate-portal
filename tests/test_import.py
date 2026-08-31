import os
import tempfile
from scripts.import_participants import import_csv
from backend.app.database import SessionLocal
from backend.app.models import Participant
from backend.app.services.participant_service import get_participant_by_email


def test_import_participants_csv(db_session, monkeypatch):
    csv_content = """email,name
User.One@Example.COM,User One
  user.two@example.com  ,User Two
invalid_email_no_at,Invalid User
user.one@example.com,User One Updated
"""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv") as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        # Patch SessionLocal in import_participants to use our test db
        monkeypatch.setattr("scripts.import_participants.SessionLocal", lambda: db_session)
        monkeypatch.setattr("scripts.import_participants.init_db", lambda: None)

        import_csv(tmp_path, default_eligible=True)

        p1 = get_participant_by_email(db_session, "user.one@example.com")
        assert p1 is not None
        assert p1.name == "User One Updated"
        assert p1.eligible is True

        p2 = get_participant_by_email(db_session, "user.two@example.com")
        assert p2 is not None
        assert p2.name == "User Two"

        p3 = get_participant_by_email(db_session, "invalid_email_no_at")
        assert p3 is None

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
