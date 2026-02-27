import uuid
from datetime import datetime as dt, timezone
from sqlalchemy import String, Enum, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    plan: Mapped[str] = mapped_column(Enum('monthly', 'yearly', name='subscription_plan_enum'), nullable=False)
    plan_type: Mapped[str] = mapped_column(Enum('employer_basic', 'employer_pro', name='subscription_plan_type_enum'), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False) # amount in UZS tiyin
    status: Mapped[str] = mapped_column(Enum('active', 'expired', 'cancelled', name='subscription_status_enum'), default='active', nullable=False)
    
    started_at: Mapped[dt] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[dt] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc), nullable=False)

    user = relationship("User")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    amount: Mapped[int] = mapped_column(Integer, nullable=False) # in tiyin
    currency: Mapped[str] = mapped_column(String(3), default='UZS', nullable=False)
    purpose: Mapped[str] = mapped_column(Enum('subscription', 'premium_vacancy', name='payment_purpose_enum'), nullable=False)
    payment_method: Mapped[str] = mapped_column(Enum('click', 'payme', 'card', name='payment_method_enum'), nullable=False)
    
    status: Mapped[str] = mapped_column(Enum('pending', 'success', 'failed', name='payment_status_enum'), default='pending', nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default=lambda: dt.now(timezone.utc), nullable=False)

    user = relationship("User")
