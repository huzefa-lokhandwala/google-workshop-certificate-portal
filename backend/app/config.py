import os
from typing import Optional
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General App Config
    APP_NAME: str = "Google Student Ambassador Workshop - Certificate Portal"
    DEBUG: bool = False
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database: Supports SQLite and external PostgreSQL (Neon / Supabase / etc.)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./backend/data/participants.db")

    # Final Certificate Template & Placement Coordinates
    CERTIFICATE_TEMPLATE_PATH: str = os.getenv(
        "CERTIFICATE_TEMPLATE_PATH", "backend/templates/certificate.pdf"
    )
    # A4 Landscape Dimensions: 841.89 pt x 595.28 pt
    # Line center is at X=420.945 pt, Y=268.88 pt; baseline sits at Y=276.0 pt
    CERTIFICATE_NAME_X: float = float(os.getenv("CERTIFICATE_NAME_X", "420.945"))
    CERTIFICATE_NAME_Y: float = float(os.getenv("CERTIFICATE_NAME_Y", "276.0"))
    CERTIFICATE_NAME_FONT_SIZE: int = int(os.getenv("CERTIFICATE_NAME_FONT_SIZE", "28"))
    CERTIFICATE_NAME_MAX_WIDTH: float = float(os.getenv("CERTIFICATE_NAME_MAX_WIDTH", "430.0"))
    CERTIFICATE_NAME_FONT: str = os.getenv("CERTIFICATE_NAME_FONT", "Helvetica-Bold")
    CERTIFICATE_CUSTOM_FONT_PATH: Optional[str] = os.getenv("CERTIFICATE_CUSTOM_FONT_PATH", None)
    CERTIFICATE_NAME_COLOR: str = os.getenv("CERTIFICATE_NAME_COLOR", "#1e293b")
    CERTIFICATE_TEXT_ALIGN: str = os.getenv("CERTIFICATE_TEXT_ALIGN", "center")  # center, left, right
    CERTIFICATE_PAGE: int = int(os.getenv("CERTIFICATE_PAGE", "0"))

    # Policy: Duplicate Generation Protection (Enforce single generation per participant)
    ALLOW_CERTIFICATE_REGENERATION: bool = os.getenv(
        "ALLOW_CERTIFICATE_REGENERATION", "false"
    ).lower() in ("true", "1", "yes")

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_MAX_REQUESTS: int = 30
    RATE_LIMIT_WINDOW_SECONDS: int = 60


@lru_cache()
def get_settings() -> Settings:
    return Settings()
