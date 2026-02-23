"""create users and otp

Revision ID: 001_create_users_and_otp
Revises: 
Create Date: 2026-02-23 10:00:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_create_users_and_otp'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    userrole = postgresql.ENUM('seeker', 'employer', 'user', 'admin', name='userrole')
    userrole.create(op.get_bind())
    
    otppurpose = postgresql.ENUM('register', 'login', 'reset', 'verify', name='otppurpose')
    otppurpose.create(op.get_bind())

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('role', postgresql.ENUM('seeker', 'employer', 'user', 'admin', name='userrole', create_type=False), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_blocked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('google_id', sa.String(length=255), nullable=True),
        sa.Column('apple_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_unique_constraint('uq_users_phone', 'users', ['phone'])
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
    op.create_unique_constraint('uq_users_google_id', 'users', ['google_id'])
    op.create_unique_constraint('uq_users_apple_id', 'users', ['apple_id'])

    op.create_table(
        'otp_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('code', sa.String(length=6), nullable=False),
        sa.Column('purpose', postgresql.ENUM('register', 'login', 'reset', 'verify', name='otppurpose', create_type=False), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('attempts', sa.SmallInteger(), nullable=False, server_default='0'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_otp_codes_phone', 'otp_codes', ['phone'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_otp_codes_phone', table_name='otp_codes')
    op.drop_table('otp_codes')
    op.drop_table('users')
    
    postgresql.ENUM(name='userrole').drop(op.get_bind())
    postgresql.ENUM(name='otppurpose').drop(op.get_bind())
