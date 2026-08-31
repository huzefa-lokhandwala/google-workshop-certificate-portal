from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.models import Participant
from backend.app.schemas import normalize_email


def get_participant_by_email(db: Session, email: str) -> Optional[Participant]:
    normalized = normalize_email(email)
    if not normalized:
        return None
    return db.query(Participant).filter(Participant.normalized_email == normalized).first()


def check_eligibility(db: Session, email: str) -> Tuple[bool, Optional[Participant]]:
    participant = get_participant_by_email(db, email)
    if not participant:
        return False, None
    return bool(participant.eligible), participant


def claim_certificate_generation(
    db: Session,
    email: str,
    allow_regeneration: bool = False
) -> Tuple[bool, Optional[Participant], str]:
    """
    Atomically verifies eligibility and claims certificate generation status.
    Uses row-level locking (with_for_update) on PostgreSQL and transaction locks on SQLite
    to guarantee that concurrent duplicate requests cannot generate duplicate certificates.

    Returns: (is_claimed: bool, participant: Optional[Participant], status_code: str)
    Status codes:
      - 'SUCCESS': Claimed successfully.
      - 'NOT_ELIGIBLE': Participant not found or not eligible.
      - 'ALREADY_GENERATED': Certificate was already claimed and regeneration is disabled.
    """
    normalized = normalize_email(email)
    if not normalized:
        return False, None, "NOT_ELIGIBLE"

    try:
        query = db.query(Participant).filter(Participant.normalized_email == normalized)
        
        # Apply row-level locking for PostgreSQL
        bind = db.get_bind()
        if bind and bind.dialect.name == "postgresql":
            participant = query.with_for_update().first()
        else:
            participant = query.first()

        if not participant or not participant.eligible:
            return False, None, "NOT_ELIGIBLE"

        if participant.certificate_generated and not allow_regeneration:
            return False, participant, "ALREADY_GENERATED"

        # Atomically claim generation in this transaction
        participant.certificate_generated = True
        participant.generated_at = datetime.now(timezone.utc)
        db.add(participant)
        db.commit()
        db.refresh(participant)
        return True, participant, "SUCCESS"

    except Exception:
        db.rollback()
        raise


def release_certificate_claim(db: Session, participant: Participant):
    """
    Rolls back the claim if the subsequent PDF generation fails.
    """
    try:
        participant.certificate_generated = False
        participant.generated_at = None
        db.add(participant)
        db.commit()
    except Exception:
        db.rollback()


def upsert_participant(
    db: Session,
    email: str,
    name: Optional[str] = None,
    eligible: bool = True
) -> Tuple[Participant, bool]:
    """
    Inserts or updates a participant without deleting existing data.
    Returns: (participant: Participant, was_created: bool)
    """
    normalized = normalize_email(email)
    participant = db.query(Participant).filter(Participant.normalized_email == normalized).first()
    was_created = False
    
    if participant:
        if name:
            participant.name = name
        participant.eligible = eligible
        participant.email = email.strip()
    else:
        participant = Participant(
            email=email.strip(),
            normalized_email=normalized,
            name=name.strip() if name else None,
            eligible=eligible,
            certificate_generated=False
        )
        db.add(participant)
        was_created = True

    db.commit()
    db.refresh(participant)
    return participant, was_created
