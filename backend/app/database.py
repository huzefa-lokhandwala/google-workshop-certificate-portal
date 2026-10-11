import os
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.config import get_settings

settings = get_settings()

def normalize_database_url(url: str) -> str:
    """
    Normalizes database URLs to ensure compatibility with SQLAlchemy and installed drivers.
    - Ensures PostgreSQL URLs explicitly use the installed 'psycopg2' driver
      (e.g., postgres://, postgresql://, postgresql+psycopg://, postgresql+psycopg3://
      -> postgresql+psycopg2://).
    - Preserves query parameters (such as ?sslmode=require).
    - Preserves SQLite and other URLs untouched.
    """
    if not url:
        return url
    url_stripped = url.strip()
    return re.sub(
        r"^(postgres|postgresql(\+psycopg[3]?)?)(://)",
        r"postgresql+psycopg2\3",
        url_stripped,
        flags=re.IGNORECASE,
    )


db_url = normalize_database_url(settings.DATABASE_URL)

# Ensure sqlite directory exists if using local sqlite file
if db_url.startswith("sqlite:///"):
    db_path = db_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend.app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
