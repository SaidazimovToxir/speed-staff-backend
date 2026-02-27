import uuid
from datetime import datetime as dt, timezone
from sqlalchemy import String, Enum, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vacancy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('vacancies.id', ondelete='CASCADE'), nullable=False, index=True)
    seeker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('seeker_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum('sent', 'viewed', 'shortlisted', 'rejected', 'hired', name='application_status_enum'), 
        default='sent', 
        nullable=False, 
        index=True
    )
    employer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    applied_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc), nullable=False)
    viewed_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc), onupdate=lambda: dt.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint('vacancy_id', 'seeker_id', name='uix_applications_vacancy_seeker'),
    )

    # Relationships
    vacancy = relationship("Vacancy", backref="applications")
    seeker = relationship("SeekerProfile", backref="applications")
