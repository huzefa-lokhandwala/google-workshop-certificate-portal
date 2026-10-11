import pytest
from sqlalchemy import create_engine
from backend.app.database import normalize_database_url


@pytest.mark.parametrize("input_url,expected_driver", [
    ("postgres://user:pass@ep-xyz.aws.neon.tech/neondb?sslmode=require", "psycopg2"),
    ("postgresql://user:pass@ep-xyz.aws.neon.tech/neondb?sslmode=require", "psycopg2"),
    ("postgresql+psycopg://user:pass@ep-xyz.aws.neon.tech/neondb?sslmode=require", "psycopg2"),
    ("postgresql+psycopg3://user:pass@ep-xyz.aws.neon.tech/neondb?sslmode=require", "psycopg2"),
    ("postgresql+psycopg2://user:pass@ep-xyz.aws.neon.tech/neondb?sslmode=require", "psycopg2"),
    ("sqlite:///./backend/data/participants.db", "pysqlite"),
    ("sqlite:///:memory:", "pysqlite"),
])
def test_normalize_database_url(input_url, expected_driver):
    normalized = normalize_database_url(input_url)
    assert "postgresql+psycopg://" not in normalized
    assert "postgresql+psycopg3://" not in normalized
    if "postgres" in input_url:
        assert normalized.startswith("postgresql+psycopg2://")
        assert "sslmode=require" in normalized
    engine = create_engine(normalized)
    assert engine.dialect.driver == expected_driver


def test_normalize_database_url_empty_or_none():
    assert normalize_database_url("") == ""
    assert normalize_database_url(None) is None
