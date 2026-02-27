"""admin_payments

Revision ID: 007_admin_payments
Revises: 006_reviews_reports
Create Date: 2026-02-26 09:00:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '007_admin_payments'
down_revision: Union[str, None] = '006_reviews_reports'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ENUMs
    subscription_plan_enum = postgresql.ENUM('monthly', 'yearly', name='subscription_plan_enum')
    subscription_plan_enum.create(op.get_bind())
    
    subscription_plan_type_enum = postgresql.ENUM('employer_basic', 'employer_pro', name='subscription_plan_type_enum')
    subscription_plan_type_enum.create(op.get_bind())
    
    subscription_status_enum = postgresql.ENUM('active', 'expired', 'cancelled', name='subscription_status_enum')
    subscription_status_enum.create(op.get_bind())
    
    payment_purpose_enum = postgresql.ENUM('subscription', 'premium_vacancy', name='payment_purpose_enum')
    payment_purpose_enum.create(op.get_bind())
    
    payment_method_enum = postgresql.ENUM('click', 'payme', 'card', name='payment_method_enum')
    payment_method_enum.create(op.get_bind())
    
    payment_status_enum = postgresql.ENUM('pending', 'success', 'failed', name='payment_status_enum')
    payment_status_enum.create(op.get_bind())

    # Subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan', postgresql.ENUM('monthly', 'yearly', name='subscription_plan_enum', create_type=False), nullable=False),
        sa.Column('plan_type', postgresql.ENUM('employer_basic', 'employer_pro', name='subscription_plan_type_enum', create_type=False), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'expired', 'cancelled', name='subscription_status_enum', create_type=False), server_default='active', nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])

    # Payments table
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='UZS', nullable=False),
        sa.Column('purpose', postgresql.ENUM('subscription', 'premium_vacancy', name='payment_purpose_enum', create_type=False), nullable=False),
        sa.Column('payment_method', postgresql.ENUM('click', 'payme', 'card', name='payment_method_enum', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'success', 'failed', name='payment_status_enum', create_type=False), server_default='pending', nullable=False),
        sa.Column('transaction_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_payments_user_id', table_name='payments')
    op.drop_table('payments')
    
    op.drop_index('ix_subscriptions_user_id', table_name='subscriptions')
    op.drop_table('subscriptions')

    postgresql.ENUM(name='payment_status_enum').drop(op.get_bind())
    postgresql.ENUM(name='payment_method_enum').drop(op.get_bind())
    postgresql.ENUM(name='payment_purpose_enum').drop(op.get_bind())
    postgresql.ENUM(name='subscription_status_enum').drop(op.get_bind())
    postgresql.ENUM(name='subscription_plan_type_enum').drop(op.get_bind())
    postgresql.ENUM(name='subscription_plan_enum').drop(op.get_bind())
