import argparse
import csv
import os
import sys

# Ensure backend package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database import SessionLocal, init_db
from backend.app.schemas import normalize_email, sanitize_name
from backend.app.services.participant_service import upsert_participant


def import_csv(file_path: str, default_eligible: bool = True):
    if not os.path.exists(file_path):
        print(f"Error: CSV file '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)

    init_db()
    db = SessionLocal()

    total_rows = 0
    inserted_count = 0
    updated_count = 0
    skipped_count = 0

    try:
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            
            email_col = next((col for col in (reader.fieldnames or []) if col and col.strip().lower() == "email"), None)
            name_col = next((col for col in (reader.fieldnames or []) if col and col.strip().lower() in ("name", "full_name", "participant_name")), None)

            if not email_col:
                print("Error: CSV must contain an 'email' column header.", file=sys.stderr)
                sys.exit(1)

            for row_idx, row in enumerate(reader, start=2):
                total_rows += 1
                raw_email = row.get(email_col, "")
                normalized = normalize_email(raw_email)
                
                # Validation: must have @ and valid domain part
                if not normalized or "@" not in normalized or "." not in normalized.split("@")[-1]:
                    skipped_count += 1
                    continue

                raw_name = row.get(name_col, "") if name_col else None
                name = sanitize_name(raw_name) if raw_name else None

                try:
                    _, was_created = upsert_participant(
                        db=db,
                        email=normalized,
                        name=name,
                        eligible=default_eligible
                    )
                    if was_created:
                        inserted_count += 1
                    else:
                        updated_count += 1
                except Exception as e:
                    skipped_count += 1

        print("\n=== Participant Import Summary ===")
        print(f"Total Rows Processed: {total_rows}")
        print(f"New Participants Inserted: {inserted_count}")
        print(f"Existing Participants Updated: {updated_count}")
        print(f"Invalid / Skipped Rows: {skipped_count}")
        print("Database sync completed successfully.")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Import workshop participants from a CSV file.")
    parser.add_argument("csv_file", help="Path to CSV file with 'email' and optional 'name' column.")
    parser.add_argument("--ineligible", action="store_true", help="Set imported participants as ineligible.")
    args = parser.parse_args()

    import_csv(args.csv_file, default_eligible=not args.ineligible)


if __name__ == "__main__":
    main()
