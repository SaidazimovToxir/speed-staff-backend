"""vacancies

Revision ID: 004_vacancies
Revises: 003_employer_profile
Create Date: 2026-02-23 16:50:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '004_vacancies'
down_revision: Union[str, None] = '003_employer_profile'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create ENUM types
    salary_type_enum = postgresql.ENUM('fixed', 'negotiable', 'hourly', name='salary_type_enum')
    salary_type_enum.create(op.get_bind())
    
    work_type_enum = postgresql.ENUM('fulltime', 'parttime', 'shift', name='work_type_enum')
    work_type_enum.create(op.get_bind())

    vacancy_status_enum = postgresql.ENUM('active', 'paused', 'closed', name='vacancy_status_enum')
    vacancy_status_enum.create(op.get_bind())

    # 2. vacancies table
    op.create_table(
        'vacancies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('employer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employer_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('position', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('requirements', sa.Text(), nullable=True),
        sa.Column('salary_min', sa.Integer(), nullable=True),
        sa.Column('salary_max', sa.Integer(), nullable=True),
        sa.Column('salary_type', postgresql.ENUM('fixed', 'negotiable', 'hourly', name='salary_type_enum', create_type=False), server_default='negotiable', nullable=False),
        sa.Column('experience_min', sa.SmallInteger(), server_default='0', nullable=False),
        sa.Column('experience_max', sa.SmallInteger(), nullable=True),
        sa.Column('work_type', postgresql.ENUM('fulltime', 'parttime', 'shift', name='work_type_enum', create_type=False), nullable=False),
        sa.Column('schedule', sa.String(length=200), nullable=True),
        sa.Column('status', postgresql.ENUM('active', 'paused', 'closed', name='vacancy_status_enum', create_type=False), server_default='active', nullable=False),
        sa.Column('is_premium', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('premium_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('views_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('applications_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    op.create_index('ix_vacancies_status', 'vacancies', ['status'])
    op.create_index('ix_vacancies_employer_id', 'vacancies', ['employer_id'])

    # 3. vacancy_skills table
    op.create_table(
        'vacancy_skills',
        sa.Column('vacancy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vacancies.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('skill_id', sa.Integer(), sa.ForeignKey('skills.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('is_required', sa.Boolean(), server_default='true', nullable=False),
    )

    # 4. saved_vacancies table
    op.create_table(
        'saved_vacancies',
        sa.Column('seeker_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('seeker_profiles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('vacancy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vacancies.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('saved_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('saved_vacancies')
    op.drop_table('vacancy_skills')
    op.drop_index('ix_vacancies_employer_id', table_name='vacancies')
    op.drop_index('ix_vacancies_status', table_name='vacancies')
    op.drop_table('vacancies')
    
    postgresql.ENUM(name='vacancy_status_enum').drop(op.get_bind())
    postgresql.ENUM(name='work_type_enum').drop(op.get_bind())
    postgresql.ENUM(name='salary_type_enum').drop(op.get_bind())
