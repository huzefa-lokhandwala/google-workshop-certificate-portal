from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from backend.app.database import Base


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    normalized_email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    eligible = Column(Boolean, default=True, nullable=False)
    certificate_generated = Column(Boolean, default=False, nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    def __repr__(self):
        return f"<Participant(id={self.id}, normalized_email='{self.normalized_email}', eligible={self.eligible})>"
