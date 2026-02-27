"""reviews_reports

Revision ID: 006_reviews_reports
Revises: 005_applications
Create Date: 2026-02-26 08:50:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '006_reviews_reports'
down_revision: Union[str, None] = '005_applications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ENUMs
    report_target_type_enum = postgresql.ENUM('vacancy', 'employer', 'seeker', 'review', name='report_target_type_enum')
    report_target_type_enum.create(op.get_bind())
    
    report_status_enum = postgresql.ENUM('pending', 'reviewed', 'dismissed', name='report_status_enum')
    report_status_enum.create(op.get_bind())

    # reviews table
    op.create_table(
        'reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('employer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employer_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rating', sa.SmallInteger(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('is_visible', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_flagged', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('employer_id', 'author_id', name='uix_reviews_employer_author'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='chk_reviews_rating_range')
    )
    op.create_index('ix_reviews_employer_id', 'reviews', ['employer_id'])
    op.create_index('ix_reviews_author_id', 'reviews', ['author_id'])

    # seeker_reviews table
    op.create_table(
        'seeker_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('seeker_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('seeker_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('employer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employer_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rating', sa.SmallInteger(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('seeker_id', 'employer_id', name='uix_seeker_reviews_seeker_employer'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='chk_seeker_reviews_rating_range')
    )
    op.create_index('ix_seeker_reviews_seeker_id', 'seeker_reviews', ['seeker_id'])
    op.create_index('ix_seeker_reviews_employer_id', 'seeker_reviews', ['employer_id'])

    # reports table
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('reporter_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_type', postgresql.ENUM('vacancy', 'employer', 'seeker', 'review', name='report_target_type_enum', create_type=False), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'reviewed', 'dismissed', name='report_status_enum', create_type=False), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_reports_reporter_id', 'reports', ['reporter_id'])
    op.create_index('ix_reports_target_type', 'reports', ['target_type'])


def downgrade() -> None:
    op.drop_index('ix_reports_target_type', table_name='reports')
    op.drop_index('ix_reports_reporter_id', table_name='reports')
    op.drop_table('reports')
    
    op.drop_index('ix_seeker_reviews_employer_id', table_name='seeker_reviews')
    op.drop_index('ix_seeker_reviews_seeker_id', table_name='seeker_reviews')
    op.drop_table('seeker_reviews')
    
    op.drop_index('ix_reviews_author_id', table_name='reviews')
    op.drop_index('ix_reviews_employer_id', table_name='reviews')
    op.drop_table('reviews')

    postgresql.ENUM(name='report_status_enum').drop(op.get_bind())
    postgresql.ENUM(name='report_target_type_enum').drop(op.get_bind())
