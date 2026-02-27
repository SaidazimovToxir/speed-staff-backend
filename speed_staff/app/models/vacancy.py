import uuid
from datetime import datetime as dt, timezone, date
from sqlalchemy import String, Boolean, Enum, SmallInteger, DateTime, Integer, Date, Numeric, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('employer_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_type: Mapped[str] = mapped_column(Enum('fixed', 'negotiable', 'hourly', name='salary_type_enum'), default='negotiable', nullable=False)
    experience_min: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    experience_max: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    work_type: Mapped[str] = mapped_column(Enum('fulltime', 'parttime', 'shift', name='work_type_enum'), nullable=False)
    schedule: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(Enum('active', 'paused', 'closed', name='vacancy_status_enum'), default='active', nullable=False, index=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    premium_until: Mapped[dt | None] = mapped_column(DateTime(timezone=True), nullable=True)
    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applications_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc), nullable=False)
    updated_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc), onupdate=lambda: dt.now(timezone.utc), nullable=False)

    employer = relationship("EmployerProfile")
    skills = relationship("VacancySkill", back_populates="vacancy", cascade="all, delete-orphan")

class VacancySkill(Base):
    __tablename__ = "vacancy_skills"

    vacancy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('vacancies.id', ondelete='CASCADE'), primary_key=True)
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey('skills.id', ondelete='CASCADE'), primary_key=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    vacancy = relationship("Vacancy", back_populates="skills")
    skill = relationship("Skill")

class SavedVacancy(Base):
    __tablename__ = "saved_vacancies"

    seeker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('seeker_profiles.id', ondelete='CASCADE'), primary_key=True)
    vacancy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('vacancies.id', ondelete='CASCADE'), primary_key=True)
    saved_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc), nullable=False)
