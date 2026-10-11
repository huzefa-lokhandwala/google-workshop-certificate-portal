import argparse
import os
import sys

# Ensure backend package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database import SessionLocal, init_db
from backend.app.models import Participant
from backend.app.schemas import normalize_email


def reset_certificates(email: str = None, reset_all: bool = False):
    init_db()
    db = SessionLocal()
    try:
        if reset_all:
            count = db.query(Participant).filter(Participant.certificate_generated == True).update(
                {Participant.certificate_generated: False, Participant.generated_at: None}
            )
            db.commit()
            print(f"Successfully reset certificate generation status for {count} participant(s).")
        elif email:
            normalized = normalize_email(email)
            participant = db.query(Participant).filter(Participant.normalized_email == normalized).first()
            if not participant:
                print(f"Error: Participant with email '{email}' not found.", file=sys.stderr)
                sys.exit(1)
            participant.certificate_generated = False
            participant.generated_at = None
            db.commit()
            print(f"Successfully reset certificate generation status for '{email}'.")
        else:
            print("Please specify an email address or use --all to reset all participants.", file=sys.stderr)
            sys.exit(1)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Reset participant certificate generation status.")
    parser.add_argument("email", nargs="?", help="Specific participant email to reset.")
    parser.add_argument("--all", action="store_true", help="Reset all participants who have generated certificates.")
    args = parser.parse_args()

    reset_certificates(email=args.email, reset_all=args.all)


if __name__ == "__main__":
    main()
