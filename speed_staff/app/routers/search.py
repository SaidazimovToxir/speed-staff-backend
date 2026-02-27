import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.vacancy import Vacancy, VacancySkill
from app.models.seeker import SeekerProfile, Skill, SeekerSkill
from app.models.employer import EmployerProfile
from app.models.user import User

from app.schemas.vacancy import VacancyShortResponse
from app.schemas.seeker import SeekerProfileShortResponse, SkillResponse
from app.schemas.employer import EmployerProfileShortResponse
from app.schemas.common import ErrorDetail, PaginatedResponse, Meta
from app.dependencies import get_current_user

router = APIRouter()

# Reuse search logic from vacancies router for public usage
@router.get("/vacancies", response_model=PaginatedResponse[VacancyShortResponse])
async def search_vacancies(
    q: Optional[str] = None,
    position: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    experience_min: Optional[int] = None,
    experience_max: Optional[int] = None,
    work_type: Optional[str] = None,
    skill_ids: List[int] = Query(None),
    city: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Vacancy).options(
        selectinload(Vacancy.employer)
    ).where(Vacancy.status == 'active')

    if q:
        search_filter = or_(
            Vacancy.title.ilike(f"%{q}%"),
            Vacancy.position.ilike(f"%{q}%"),
            Vacancy.description.ilike(f"%{q}%")
        )
        stmt = stmt.where(search_filter)

    if position:
        stmt = stmt.where(Vacancy.position.ilike(f"%{position}%"))
    if salary_min is not None:
        stmt = stmt.where(or_(Vacancy.salary_max >= salary_min, Vacancy.salary_max.is_(None)))
    if salary_max is not None:
        stmt = stmt.where(or_(Vacancy.salary_min <= salary_max, Vacancy.salary_min.is_(None)))
    if experience_min is not None:
        stmt = stmt.where(Vacancy.experience_min >= experience_min)
    if experience_max is not None:
        stmt = stmt.where(or_(Vacancy.experience_max <= experience_max, Vacancy.experience_max.is_(None)))
    if work_type:
        stmt = stmt.where(Vacancy.work_type == work_type)
    if city:
        stmt = stmt.join(EmployerProfile).where(EmployerProfile.city.ilike(f"%{city}%"))
    if skill_ids:
        stmt = stmt.join(VacancySkill).where(VacancySkill.skill_id.in_(skill_ids))

    count_stmt = select(func.count(Vacancy.id)).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.order_by(Vacancy.is_premium.desc(), Vacancy.created_at.desc())
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    vacancies = result.scalars().unique().all()
    
    pages = (total + limit - 1) // limit if total else 0
    meta = Meta(page=page, limit=limit, total=total, pages=pages, has_next=page < pages, has_prev=page > 1)
    
    return PaginatedResponse(items=[VacancyShortResponse.model_validate(v) for v in vacancies], meta=meta)


@router.get("/seekers", response_model=PaginatedResponse[SeekerProfileShortResponse])
async def search_seekers(
    position: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    experience_min: Optional[int] = None,
    experience_max: Optional[int] = None,
    skill_ids: List[int] = Query(None),
    is_available: Optional[bool] = None,
    city: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["employer", "admin"]:
        return JSONResponse(status_code=403, content=ErrorDetail(error_code="NOT_AUTHORIZED", message="Only employers or admins can search seekers").model_dump())

    stmt = select(SeekerProfile)
    
    # We will derive latest 'position' for the shortcut response later
    from app.models.seeker import WorkExperience
    
    if position:
        stmt = stmt.join(WorkExperience).where(WorkExperience.position.ilike(f"%{position}%"))
    if salary_min is not None:
        stmt = stmt.where(or_(SeekerProfile.expected_salary_max >= salary_min, SeekerProfile.expected_salary_max.is_(None)))
    if salary_max is not None:
        stmt = stmt.where(or_(SeekerProfile.expected_salary_min <= salary_max, SeekerProfile.expected_salary_min.is_(None)))
    if experience_min is not None:
        stmt = stmt.where(SeekerProfile.experience_years >= experience_min)
    if experience_max is not None:
        stmt = stmt.where(SeekerProfile.experience_years <= experience_max)
    if is_available is not None:
        stmt = stmt.where(SeekerProfile.is_available == is_available)
    if city:
        stmt = stmt.where(SeekerProfile.city.ilike(f"%{city}%"))
    if skill_ids:
        stmt = stmt.join(SeekerSkill).where(SeekerSkill.skill_id.in_(skill_ids))

    count_stmt = select(func.count(SeekerProfile.id)).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.order_by(SeekerProfile.created_at.desc())
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    seekers = result.scalars().unique().all()
    
    pages = (total + limit - 1) // limit if total else 0
    meta = Meta(page=page, limit=limit, total=total, pages=pages, has_next=page < pages, has_prev=page > 1)
    
    return PaginatedResponse(items=[SeekerProfileShortResponse.model_validate(s) for s in seekers], meta=meta)


@router.get("/employers", response_model=PaginatedResponse[EmployerProfileShortResponse])
async def search_employers(
    q: Optional[str] = None,
    city: Optional[str] = None,
    is_verified: Optional[bool] = None,
    min_rating: Optional[float] = None,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(EmployerProfile)

    if q:
        stmt = stmt.where(EmployerProfile.restaurant_name.ilike(f"%{q}%"))
    if city:
        stmt = stmt.where(EmployerProfile.city.ilike(f"%{city}%"))
    if is_verified is not None:
        stmt = stmt.where(EmployerProfile.is_verified == is_verified)
    if min_rating is not None:
        stmt = stmt.where(EmployerProfile.rating >= min_rating)

    count_stmt = select(func.count(EmployerProfile.id)).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.order_by(EmployerProfile.rating.desc(), EmployerProfile.created_at.desc())
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    employers = result.scalars().all()
    
    pages = (total + limit - 1) // limit if total else 0
    meta = Meta(page=page, limit=limit, total=total, pages=pages, has_next=page < pages, has_prev=page > 1)

    return PaginatedResponse(items=[EmployerProfileShortResponse.model_validate(e) for e in employers], meta=meta)


@router.get("/skills", response_model=List[SkillResponse])
async def search_skills(
    q: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Skill)
    
    if q:
        search_filter = or_(
            Skill.name_uz.ilike(f"%{q}%"),
            Skill.name_ru.ilike(f"%{q}%")
        )
        stmt = stmt.where(search_filter)
        
    if category:
        stmt = stmt.where(Skill.category == category)
        
    result = await db.execute(stmt)
    skills = result.scalars().all()
    
    return [SkillResponse.model_validate(s) for s in skills]
