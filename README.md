# Google Meet / Google Student Ambassador Workshop - Certificate Portal

A lightweight, secure, and production-ready certificate verification and dynamic PDF generation portal built with FastAPI, ReportLab, and SQLAlchemy, optimized for deployment on Render.

## Features

- **Private Participant Verification**: Email authorization check against a SQLite or external PostgreSQL database without exposing the participant list.
- **Pure Vector PDF Overlay Engine**: Uses ReportLab & pypdf to dynamically place participant names onto the official workshop certificate template with zero rasterization and no image quality loss.
- **Smart Name Auto-Scaling**: Automatically calculates name width and scales font size so long names never overflow the template's designated name area.
- **Render Persistence Ready**: Fully supports persistent, free cloud databases (such as Neon or Supabase PostgreSQL) via `DATABASE_URL` with zero recurring costs.
- **Duplicate Generation Protection**: Configurable policy (`ALLOW_CERTIFICATE_REGENERATION=false`) prevents repeated certificate generation abuse.
- **Prominent Name Warning UI**: Highlights the one-time generation policy and prompts participants to enter and verify their exact full name.
- **Participant CSV Importer**: CLI tool to import, normalize, and update workshop participant lists.

---

## Directory Structure

```
├── backend/
│   ├── app/
│   │   ├── config.py              # Application settings & environment variables
│   │   ├── database.py            # SQLite / PostgreSQL SQLAlchemy database engine
│   │   ├── models.py              # Participant ORM model
│   │   ├── schemas.py             # Pydantic models, name sanitization & validation
│   │   ├── main.py                # FastAPI application, rate limiter & static mount
│   │   ├── routes/                # Health, Verification, and Certificate endpoints
│   │   └── services/              # Participant & PDF Overlay services
│   ├── data/                      # Local SQLite database storage (participants.db)
│   └── templates/
│       └── certificate.pdf        # Official workshop certificate PDF template
├── frontend/
│   ├── index.html                 # Mobile-first portal UI with name warning banner
│   ├── css/styles.css             # Design system styling
│   └── js/app.js                  # Frontend client logic & blob download
├── scripts/
│   └── import_participants.py     # Participant list CSV importer
├── tests/                         # Comprehensive pytest automated test suite (35 tests)
├── requirements.txt               # Production Python dependencies
└── render.yaml                    # Render Web Service blueprint
```

---

## Local Development Setup

### 1. Prerequisites
- Python 3.10+

### 2. Setup Virtual Environment & Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Import Authorized Workshop Participants
Prepare a CSV file (e.g. `participants.csv`) with `email` and optional `name` columns:
```csv
email,name
jane.doe@example.com,Jane Doe
john.smith@example.com,John Smith
```
Run the import command:
```bash
python scripts/import_participants.py participants.csv
```

### 4. Start the Application Server
```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
Open your browser at `http://localhost:8000`.

---

## Running Automated Tests

Run the full automated test suite:
```bash
pytest -v
```

---

## Environment Variables & Certificate Customization

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | Server listening port (Render automatically provides this) |
| `DATABASE_URL` | `sqlite:///./backend/data/participants.db` | Connection string. For Render persistence, set to your free PostgreSQL connection URI (e.g. Neon or Supabase) |
| `CERTIFICATE_TEMPLATE_PATH` | `backend/templates/certificate.pdf` | Path to the PDF certificate template |
| `CERTIFICATE_NAME_X` | `420.945` | Center X coordinate in PDF points (A4 width 841.89 pt) |
| `CERTIFICATE_NAME_Y` | `276.0` | Y coordinate in PDF points for participant name (above line at Y=268.88 pt) |
| `CERTIFICATE_NAME_FONT_SIZE` | `28` | Base font size in points (auto-scaled for long names) |
| `CERTIFICATE_NAME_MAX_WIDTH` | `430.0` | Maximum allowed width in points on the name line before auto-scaling |
| `CERTIFICATE_NAME_FONT` | `Helvetica-Bold` | Font name (e.g. `Helvetica-Bold`, `Times-Bold`) |
| `CERTIFICATE_CUSTOM_FONT_PATH` | `None` | Optional path to a custom TrueType font (.ttf) |
| `CERTIFICATE_NAME_COLOR` | `#1e293b` | Hex text color |
| `CERTIFICATE_TEXT_ALIGN` | `center` | Text alignment (`center`, `left`, or `right`) |
| `CERTIFICATE_PAGE` | `0` | 0-indexed page number of the template to overlay text |
| `ALLOW_CERTIFICATE_REGENERATION` | `false` | When `false`, blocks repeated certificate generations for an email |

---

## Deploying to Render (₹0 Cost with Free Persistent Database)

Render's free web services run on ephemeral disks. To ensure participant eligibility and `certificate_generated` statuses persist permanently across redeploys and restarts at ₹0 cost:

1. **Create a Free PostgreSQL Database**:
   - Go to [Neon.tech](https://neon.tech) (Free Tier: 0.5 GB Postgres, always free) or [Supabase](https://supabase.com).
   - Copy your Postgres connection string (e.g., `postgresql://user:pass@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require`).
2. **Import Participants into Remote Database**:
   ```bash
   DATABASE_URL="your-neon-postgres-url" python scripts/import_participants.py your_participants.csv
   ```
3. **Deploy on Render**:
   - Push this repository to GitHub/GitLab.
   - On Render, create a new **Web Service** from your repository.
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables**:
     - `DATABASE_URL`: paste your Neon/Supabase PostgreSQL connection string.
     - `ALLOW_CERTIFICATE_REGENERATION`: `false`
   - **Health Check Path**: `/health`
