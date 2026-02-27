import uuid
from datetime import datetime as dt, timezone
from sqlalchemy import String, Boolean, Enum, SmallInteger, DateTime, Text, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('employer_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint('employer_id', 'author_id', name='uix_reviews_employer_author'),
        CheckConstraint('rating >= 1 AND rating <= 5', name='chk_reviews_rating_range')
    )

    employer = relationship("EmployerProfile", backref="reviews")
    author = relationship("User")


class SeekerReview(Base):
    __tablename__ = "seeker_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seeker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('seeker_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    employer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('employer_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint('seeker_id', 'employer_id', name='uix_seeker_reviews_seeker_employer'),
        CheckConstraint('rating >= 1 AND rating <= 5', name='chk_seeker_reviews_rating_range')
    )

    seeker = relationship("SeekerProfile", backref="seeker_reviews")
    employer = relationship("EmployerProfile")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    target_type: Mapped[str] = mapped_column(Enum('vacancy', 'employer', 'seeker', 'review', name='report_target_type_enum'), nullable=False, index=True)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    status: Mapped[str] = mapped_column(Enum('pending', 'reviewed', 'dismissed', name='report_status_enum'), default='pending', nullable=False)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc), nullable=False)

    reporter = relationship("User")
