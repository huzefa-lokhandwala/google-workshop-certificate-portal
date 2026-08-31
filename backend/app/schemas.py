import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


def normalize_email(email: str) -> str:
    if not email:
        return ""
    return email.strip().lower()


def sanitize_name(name: str) -> str:
    if not name:
        return ""
    return re.sub(r"\s+", " ", name.strip())


class VerifyRequest(BaseModel):
    email: EmailStr

    @field_validator("email", mode="after")
    @classmethod
    def normalize_input_email(cls, v: EmailStr) -> str:
        return normalize_email(str(v))


class VerifyResponse(BaseModel):
    eligible: bool
    message: str


class GenerateCertificateRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., description="Full Name of participant")

    @field_validator("email", mode="after")
    @classmethod
    def normalize_input_email(cls, v: EmailStr) -> str:
        return normalize_email(str(v))

    @field_validator("name", mode="before")
    @classmethod
    def validate_raw_name(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Participant name must be a string.")
        # Reject control characters, script tags, newlines, or path traversal symbols
        if any(char in v for char in ["\n", "\r", "\t", "\0", "<", ">", "{", "}", "\\", "/"]):
            raise ValueError("Participant name contains invalid characters.")
        cleaned = sanitize_name(v)
        if len(cleaned) < 2:
            raise ValueError("Participant name must be at least 2 characters long.")
        if len(cleaned) > 100:
            raise ValueError("Participant name cannot exceed 100 characters.")
        return cleaned


class ParticipantImportItem(BaseModel):
    email: str
    name: Optional[str] = None
    eligible: bool = True
