"""seed_english_skills

Revision ID: 009_seed_english_skills
Revises: 008_add_lat_long_name_en
Create Date: 2026-02-26 10:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String

revision: str = '009_seed_english_skills'
down_revision: Union[str, None] = '008_add_lat_long_name_en'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    skills = table('skills',
        column('name_uz', String),
        column('name_ru', String),
        column('name_en', String),
        column('category', String)
    )

    # 1. Update existing skills with English translations
    updates = [
        ("Xizmat ko'rsatish", "Customer Service"),
        ("Menyu bilish", "Menu Knowledge"),
        ("Buyurtma qabul qilish", "Order Taking"),
        ("Hisob-kitob qilish", "Billing & Checkout"),
        ("Kofe tayyorlash", "Coffee Making"),
        ("Kokteyl tayyorlash", "Cocktail Making"),
        ("Vino bilish", "Wine Knowledge"),
        ("Issiq taomlar", "Hot Dishes"),
        ("Sovuq taomlar", "Cold Dishes"),
        ("Sushi", "Sushi Preparation"),
        ("Pizza", "Pizza Making"),
        ("Milliy taomlar", "National Cuisine"),
        ("Jamoa boshqarish", "Team Management"),
        ("Kassa", "Cashier / POS"),
        ("Inventarizatsiya", "Inventory Management"),
    ]
    
    for uz_name, en_name in updates:
        op.execute(
            skills.update().where(skills.c.name_uz == uz_name).values(name_en=en_name)
        )

    # 2. Insert new useful restaurant skills
    new_skills = [
        {'name_uz': "Tozalik va sanitariya", 'name_ru': "Уборка и санитария", 'name_en': "Cleaning & Sanitation", 'category': "service"},
        {'name_uz': "Xorijiy tillar", 'name_ru': "Иностранные языки", 'name_en': "Foreign Languages", 'category': "service"},
        {'name_uz': "Mojarolarni hal qilish", 'name_ru': "Разрешение конфликтов", 'name_en': "Conflict Resolution", 'category': "service"},
        {'name_uz': "Banket xizmati", 'name_ru': "Банкетное обслуживание", 'name_en': "Banquet Service", 'category': "service"},
        {'name_uz': "Fast food tayyorlash", 'name_ru': "Приготовление фаст-фуда", 'name_en': "Fast Food Preparation", 'category': "food"},
        {'name_uz': "Pishiriqlar", 'name_ru': "Выпечка и десерты", 'name_en': "Baking & Desserts", 'category': "food"},
        {'name_uz': "Yetkazib berish", 'name_ru': "Доставка", 'name_en': "Delivery", 'category': "service"},
        {'name_uz': "Marketing va SMM", 'name_ru': "Маркетинг и SMM", 'name_en': "Marketing & SMM", 'category': "management"},
        {'name_uz': "Xaridlar", 'name_ru': "Закупки", 'name_en': "Purchasing", 'category': "management"},
    ]
    
    op.bulk_insert(skills, new_skills)


def downgrade() -> None:
    # Remove newly added skills
    op.execute("DELETE FROM skills WHERE name_en IN ('Cleaning & Sanitation', 'Foreign Languages', 'Conflict Resolution', 'Banquet Service', 'Fast Food Preparation', 'Baking & Desserts', 'Delivery', 'Marketing & SMM', 'Purchasing')")
    # Reset name_en for original skills
    op.execute("UPDATE skills SET name_en = NULL")
