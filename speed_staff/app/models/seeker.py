import uuid
from datetime import datetime as dt, timezone, date
from sqlalchemy import String, Boolean, Enum, SmallInteger, DateTime, Integer, Date, Numeric, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

class SeekerProfile(Base):
    __tablename__ = "seeker_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(Enum('male', 'female', name='gender_enum'), nullable=True)
    experience_years: Mapped[int] = mapped_column(SmallInteger, default=0)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expected_salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    resume_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rating: Mapped[float] = mapped_column(Numeric(2, 1), default=0.0)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc))
    updated_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc), onupdate=lambda: dt.now(timezone.utc))

    user = relationship("User", backref="seeker_profile", uselist=False)
    skills = relationship("SeekerSkill", back_populates="seeker", cascade="all, delete-orphan")
    experiences = relationship("WorkExperience", back_populates="seeker", cascade="all, delete-orphan")
    documents = relationship("SeekerDocument", back_populates="seeker", cascade="all, delete-orphan")

class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name_uz: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ru: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name_en: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    seeker_links = relationship("SeekerSkill", back_populates="skill")

class SeekerSkill(Base):
    __tablename__ = "seeker_skills"

    seeker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('seeker_profiles.id', ondelete='CASCADE'), primary_key=True)
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey('skills.id', ondelete='CASCADE'), primary_key=True)
    level: Mapped[str] = mapped_column(Enum('beginner', 'intermediate', 'expert', name='skill_level_enum'), default='beginner', nullable=False)

    seeker = relationship("SeekerProfile", back_populates="skills")
    skill = relationship("Skill", back_populates="seeker_links")

class WorkExperience(Base):
    __tablename__ = "work_experiences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seeker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('seeker_profiles.id', ondelete='CASCADE'), nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc))

    seeker = relationship("SeekerProfile", back_populates="experiences")

class SeekerDocument(Base):
    __tablename__ = "seeker_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seeker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('seeker_profiles.id', ondelete='CASCADE'), nullable=False)
    doc_type: Mapped[str] = mapped_column(Enum('passport', 'certificate', 'diploma', 'other', name='doc_type_enum'), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc))

    seeker = relationship("SeekerProfile", back_populates="documents")
