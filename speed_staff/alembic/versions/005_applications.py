"""applications

Revision ID: 005_applications
Revises: 004_vacancies
Create Date: 2026-02-24 09:20:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '005_applications'
down_revision: Union[str, None] = '004_vacancies'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ENUM
    application_status_enum = postgresql.ENUM('sent', 'viewed', 'shortlisted', 'rejected', 'hired', name='application_status_enum')
    application_status_enum.create(op.get_bind())

    # Create applications table
    op.create_table(
        'applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vacancy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vacancies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('seeker_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('seeker_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cover_letter', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM('sent', 'viewed', 'shortlisted', 'rejected', 'hired', name='application_status_enum', create_type=False), server_default='sent', nullable=False),
        sa.Column('employer_note', sa.Text(), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('viewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('vacancy_id', 'seeker_id', name='uix_applications_vacancy_seeker')
    )

    op.create_index('ix_applications_seeker_id', 'applications', ['seeker_id'])
    op.create_index('ix_applications_vacancy_id', 'applications', ['vacancy_id'])
    op.create_index('ix_applications_status', 'applications', ['status'])


def downgrade() -> None:
    op.drop_index('ix_applications_status', table_name='applications')
    op.drop_index('ix_applications_vacancy_id', table_name='applications')
    op.drop_index('ix_applications_seeker_id', table_name='applications')
    op.drop_table('applications')
    postgresql.ENUM(name='application_status_enum').drop(op.get_bind())
