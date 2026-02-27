import uuid
from datetime import datetime as dt, timezone, date
from sqlalchemy import String, Boolean, Enum, SmallInteger, DateTime, Integer, Date, Numeric, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

class EmployerProfile(Base):
    __tablename__ = "employer_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    restaurant_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    website: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[float] = mapped_column(Numeric(2, 1), default=0.0)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc))
    updated_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc), onupdate=lambda: dt.now(timezone.utc))

    user = relationship("User", backref="employer_profile", uselist=False)
