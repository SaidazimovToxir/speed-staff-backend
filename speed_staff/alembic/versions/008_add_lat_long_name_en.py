"""add_lat_long_name_en

Revision ID: 008_add_lat_long_name_en
Revises: 007_admin_payments
Create Date: 2026-02-26 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '008_add_lat_long_name_en'
down_revision: Union[str, None] = '007_admin_payments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('employer_profiles', sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=True))
    op.add_column('employer_profiles', sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=True))
    op.add_column('skills', sa.Column('name_en', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('skills', 'name_en')
    op.drop_column('employer_profiles', 'longitude')
    op.drop_column('employer_profiles', 'latitude')
