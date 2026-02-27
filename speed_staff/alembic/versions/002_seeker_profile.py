"""seeker profile

Revision ID: 002_seeker_profile
Revises: 001_create_users_and_otp
Create Date: 2026-02-23 16:30:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '002_seeker_profile'
down_revision: Union[str, None] = '001_create_users_and_otp'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ENUMS
    gender_enum = postgresql.ENUM('male', 'female', name='gender_enum')
    gender_enum.create(op.get_bind())
    
    skill_level_enum = postgresql.ENUM('beginner', 'intermediate', 'expert', name='skill_level_enum')
    skill_level_enum.create(op.get_bind())
    
    doc_type_enum = postgresql.ENUM('passport', 'certificate', 'diploma', 'other', name='doc_type_enum')
    doc_type_enum.create(op.get_bind())

    # 2. TABLES
    # skills
    skills_table = op.create_table(
        'skills',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name_uz', sa.String(length=100), nullable=False),
        sa.Column('name_ru', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # seeker_profiles
    op.create_table(
        'seeker_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('middle_name', sa.String(length=100), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('gender', postgresql.ENUM('male', 'female', name='gender_enum', create_type=False), nullable=True),
        sa.Column('experience_years', sa.SmallInteger(), nullable=False, server_default='0'),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('expected_salary_min', sa.Integer(), nullable=True),
        sa.Column('expected_salary_max', sa.Integer(), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('resume_url', sa.String(length=500), nullable=True),
        sa.Column('rating', sa.Numeric(precision=2, scale=1), nullable=False, server_default='0.0'),
        sa.Column('total_reviews', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id')
    )

    # seeker_skills
    op.create_table(
        'seeker_skills',
        sa.Column('seeker_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('skill_id', sa.Integer(), nullable=False),
        sa.Column('level', postgresql.ENUM('beginner', 'intermediate', 'expert', name='skill_level_enum', create_type=False), nullable=False, server_default='beginner'),
        sa.ForeignKeyConstraint(['seeker_id'], ['seeker_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('seeker_id', 'skill_id')
    )

    # work_experiences
    op.create_table(
        'work_experiences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('seeker_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_name', sa.String(length=200), nullable=False),
        sa.Column('position', sa.String(length=100), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['seeker_id'], ['seeker_profiles.id'], ondelete='CASCADE')
    )

    # seeker_documents
    op.create_table(
        'seeker_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('seeker_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('doc_type', postgresql.ENUM('passport', 'certificate', 'diploma', 'other', name='doc_type_enum', create_type=False), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('file_url', sa.String(length=500), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['seeker_id'], ['seeker_profiles.id'], ondelete='CASCADE')
    )

    # 3. SEED INITIAL DATA
    op.bulk_insert(
        skills_table,
        [
            {'name_uz': "Xizmat ko'rsatish", 'name_ru': "Обслуживание клиентов", 'category': "service"},
            {'name_uz': "Menyu bilish", 'name_ru': "Знание меню", 'category': "service"},
            {'name_uz': "Buyurtma qabul qilish", 'name_ru': "Приём заказов", 'category': "service"},
            {'name_uz': "Hisob-kitob qilish", 'name_ru': "Расчёт клиентов", 'category': "service"},
            
            {'name_uz': "Kofe tayyorlash", 'name_ru': "Приготовление кофе", 'category': "drinks"},
            {'name_uz': "Kokteyl tayyorlash", 'name_ru': "Приготовление коктейлей", 'category': "drinks"},
            {'name_uz': "Vino bilish", 'name_ru': "Знание вин", 'category': "drinks"},
            
            {'name_uz': "Issiq taomlar", 'name_ru': "Горячие блюда", 'category': "food"},
            {'name_uz': "Sovuq taomlar", 'name_ru': "Холодные блюда", 'category': "food"},
            {'name_uz': "Sushi", 'name_ru': "Суши", 'category': "food"},
            {'name_uz': "Pizza", 'name_ru': "Пицца", 'category': "food"},
            {'name_uz': "Milliy taomlar", 'name_ru': "Национальные блюда", 'category': "food"},
            
            {'name_uz': "Jamoa boshqarish", 'name_ru': "Управление командой", 'category': "management"},
            {'name_uz': "Kassa", 'name_ru': "Касса", 'category': "management"},
            {'name_uz': "Inventarizatsiya", 'name_ru': "Инвентаризация", 'category': "management"},
        ]
    )

def downgrade() -> None:
    op.drop_table('seeker_documents')
    op.drop_table('work_experiences')
    op.drop_table('seeker_skills')
    op.drop_table('seeker_profiles')
    op.drop_table('skills')
    
    postgresql.ENUM(name='doc_type_enum').drop(op.get_bind())
    postgresql.ENUM(name='skill_level_enum').drop(op.get_bind())
    postgresql.ENUM(name='gender_enum').drop(op.get_bind())
