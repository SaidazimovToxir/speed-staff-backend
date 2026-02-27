import uuid
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update
from sqlalchemy.orm import selectinload

from app.database import get_db, async_sessionmaker, engine
from app.models.vacancy import Vacancy, VacancySkill, SavedVacancy
from app.models.seeker import Skill
from app.models.employer import EmployerProfile
from app.models.user import User
from app.schemas.vacancy import (
    VacancyCreate, VacancyUpdate, VacancyResponse, VacancyShortResponse, VacancyStatusUpdate, VacancySkillItem
)
from app.schemas.common import ErrorDetail, SuccessResponse, PaginatedResponse, Meta
from app.dependencies import get_current_user

router = APIRouter()

def error_response(code: str, message: str, status_code: int, details=None):
    return JSONResponse(
        status_code=status_code,
        content=ErrorDetail(error_code=code, message=message, details=details).model_dump()
    )


# --- Public Feed ---
@router.get("", response_model=PaginatedResponse[VacancyShortResponse])
async def list_vacancies(
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

    if position:
        stmt = stmt.where(Vacancy.position.ilike(f"%{position}%"))
    if salary_min is not None:
        # Either salary_max >= required_min OR no max salary set
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

    # Calculate total for pagination
    count_stmt = select(func.count(Vacancy.id)).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    # Order and Limit
    stmt = stmt.order_by(Vacancy.is_premium.desc(), Vacancy.created_at.desc())
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    vacancies = result.scalars().unique().all()
    
    pages = (total + limit - 1) // limit if total else 0
    meta = Meta(page=page, limit=limit, total=total, pages=pages, has_next=page < pages, has_prev=page > 1)
    
    return PaginatedResponse(items=[VacancyShortResponse.model_validate(v) for v in vacancies], meta=meta)


def increment_views_sync(vacancy_id: uuid.UUID):
    # Fast background task to increment view count without blocking
    import asyncio
    async def _increment():
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            stmt = update(Vacancy).where(Vacancy.id == vacancy_id).values(views_count=Vacancy.views_count + 1)
            await session.execute(stmt)
            await session.commit()
    
    asyncio.create_task(_increment())


@router.get("/{vacancy_id}", response_model=VacancyResponse | ErrorDetail)
async def get_vacancy(vacancy_id: uuid.UUID, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    stmt = select(Vacancy).options(
        selectinload(Vacancy.employer),
        selectinload(Vacancy.skills).selectinload(VacancySkill.skill)
    ).where(Vacancy.id == vacancy_id)
    
    result = await db.execute(stmt)
    vacancy = result.scalars().first()
    
    if not vacancy:
        return error_response("VACANCY_NOT_FOUND", "Vacancy doesn't exist", 404)

    # Background view count tracking
    background_tasks.add_task(increment_views_sync, vacancy_id)

    return VacancyResponse.model_validate(vacancy)


# --- Employer Operations ---
@router.post("", response_model=VacancyResponse | ErrorDetail)
async def create_vacancy(
    request: VacancyCreate, 
    skills: List[VacancySkillItem] = None, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "employer":
        return error_response("NOT_AUTHORIZED", "Available only for employers", 403)
        
    employer_stmt = select(EmployerProfile.id).where(EmployerProfile.user_id == current_user.id)
    employer_id = await db.scalar(employer_stmt)
    if not employer_id:
        return error_response("PROFILE_NOT_FOUND", "Create employer profile first", 404)

    # Limit check
    active_count_stmt = select(func.count(Vacancy.id)).where(Vacancy.employer_id == employer_id, Vacancy.status == 'active')
    active_count = await db.scalar(active_count_stmt)
    
    if active_count >= 3:
        # TODO: Add premium checks here later in subscription module sprint
        return error_response("VACANCY_LIMIT_REACHED", "Limit of 3 active vacancies reached", 400)

    vacancy_data = request.model_dump()
    vacancy = Vacancy(**vacancy_data, employer_id=employer_id)
    db.add(vacancy)
    await db.flush()

    if skills:
        for sk in skills:
            v_skill = VacancySkill(vacancy_id=vacancy.id, skill_id=sk.skill_id, is_required=sk.is_required)
            db.add(v_skill)
            
    await db.commit()
    
    # Reload with relations
    load_stmt = select(Vacancy).options(
        selectinload(Vacancy.employer),
        selectinload(Vacancy.skills).selectinload(VacancySkill.skill)
    ).where(Vacancy.id == vacancy.id)
    result = await db.execute(load_stmt)
    
    return VacancyResponse.model_validate(result.scalars().first())


@router.put("/{vacancy_id}", response_model=VacancyResponse | ErrorDetail)
async def update_vacancy(
    vacancy_id: uuid.UUID, 
    request: VacancyUpdate, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    employer_stmt = select(EmployerProfile.id).where(EmployerProfile.user_id == current_user.id)
    employer_id = await db.scalar(employer_stmt)

    stmt = select(Vacancy).where(Vacancy.id == vacancy_id)
    result = await db.execute(stmt)
    vacancy = result.scalars().first()

    if not vacancy or vacancy.employer_id != employer_id:
        return error_response("NOT_YOUR_RECORD", "Vacancy not found or not yours", 403)

    if vacancy.status == 'closed':
        return error_response("VACANCY_CLOSED", "Cannot edit closed vacancy", 400)

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(vacancy, key, value)
        
    await db.commit()
    
    load_stmt = select(Vacancy).options(
        selectinload(Vacancy.employer),
        selectinload(Vacancy.skills).selectinload(VacancySkill.skill)
    ).where(Vacancy.id == vacancy_id)
    res = await db.execute(load_stmt)
    
    return VacancyResponse.model_validate(res.scalars().first())


@router.patch("/{vacancy_id}/status", response_model=SuccessResponse | ErrorDetail)
async def change_status(
    vacancy_id: uuid.UUID, 
    request: VacancyStatusUpdate, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Vacancy).where(Vacancy.id == vacancy_id)
    result = await db.execute(stmt)
    vacancy = result.scalars().first()

    if not vacancy:
        return error_response("VACANCY_NOT_FOUND", "Vacancy not found", 404)

    if current_user.role != "admin":
        employer_stmt = select(EmployerProfile.id).where(EmployerProfile.user_id == current_user.id)
        employer_id = await db.scalar(employer_stmt)
        if vacancy.employer_id != employer_id:
            return error_response("NOT_YOUR_RECORD", "Vacancy not found or not yours", 403)

    if vacancy.status == 'closed' and request.status != 'closed':
        return error_response("VACANCY_ALREADY_CLOSED", "Cannot reopen closed vacancy", 400)

    vacancy.status = request.status
    await db.commit()
    return SuccessResponse(message=f"Vacancy status set to {request.status}")


@router.delete("/{vacancy_id}", response_model=SuccessResponse | ErrorDetail)
async def delete_vacancy(vacancy_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Vacancy).where(Vacancy.id == vacancy_id)
    result = await db.execute(stmt)
    vacancy = result.scalars().first()

    if not vacancy:
        return error_response("VACANCY_NOT_FOUND", "Vacancy not found", 404)

    if current_user.role != "admin":
        employer_stmt = select(EmployerProfile.id).where(EmployerProfile.user_id == current_user.id)
        employer_id = await db.scalar(employer_stmt)
        if vacancy.employer_id != employer_id:
            return error_response("NOT_YOUR_RECORD", "Vacancy not found or not yours", 403)

    # Soft delete approach - transition to closed
    vacancy.status = 'closed'
    await db.commit()
    return SuccessResponse(message="Vacancy closed")


from app.models.application import Application
from app.schemas.application import ApplicationShortResponse

@router.get("/{vacancy_id}/applications", response_model=PaginatedResponse[ApplicationShortResponse] | ErrorDetail)
async def get_vacancy_applications(
    vacancy_id: uuid.UUID, 
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Vacancy).options(selectinload(Vacancy.employer)).where(Vacancy.id == vacancy_id)
    result = await db.execute(stmt)
    vacancy = result.scalars().first()

    if not vacancy:
        return error_response("VACANCY_NOT_FOUND", "Vacancy not found", 404)

    is_employer = current_user.role == "employer" and vacancy.employer.user_id == current_user.id
    is_admin = current_user.role == "admin"

    if not (is_employer or is_admin):
        return error_response("NOT_YOUR_RECORD", "Not authorized to view", 403)

    app_stmt = select(Application).options(
        selectinload(Application.seeker)
    ).where(Application.vacancy_id == vacancy.id)

    if status:
        app_stmt = app_stmt.where(Application.status == status)

    count_stmt = select(func.count(Application.id)).select_from(app_stmt.subquery())
    total = await db.scalar(count_stmt)

    app_stmt = app_stmt.order_by(Application.applied_at.desc())
    offset = (page - 1) * limit
    app_stmt = app_stmt.offset(offset).limit(limit)

    res = await db.execute(app_stmt)
    applications = res.scalars().all()

    pages = (total + limit - 1) // limit if total else 0
    meta = Meta(page=page, limit=limit, total=total, pages=pages, has_next=page < pages, has_prev=page > 1)

    return PaginatedResponse(items=[ApplicationShortResponse.model_validate(a) for a in applications], meta=meta)


# --- Seeker Bookmarks Operations ---
@router.post("/{vacancy_id}/save", response_model=SuccessResponse | ErrorDetail)
async def save_vacancy(vacancy_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "seeker":
        return error_response("NOT_AUTHORIZED", "Available only for seekers", 403)
        
    # Get seeker Profile
    from app.models.seeker import SeekerProfile
    seeker_stmt = select(SeekerProfile.id).where(SeekerProfile.user_id == current_user.id)
    seeker_id = await db.scalar(seeker_stmt)
    if not seeker_id:
        return error_response("PROFILE_NOT_FOUND", "Create profile first", 404)
        
    checking_stmt = select(SavedVacancy).where(SavedVacancy.seeker_id == seeker_id, SavedVacancy.vacancy_id == vacancy_id)
    if await db.scalar(checking_stmt):
        return error_response("ALREADY_SAVED", "Vacancy already bookmarked", 409)

    saved_vac = SavedVacancy(seeker_id=seeker_id, vacancy_id=vacancy_id)
    db.add(saved_vac)
    await db.commit()
    return SuccessResponse(message="Vacancy saved")


@router.delete("/{vacancy_id}/save", response_model=SuccessResponse | ErrorDetail)
async def remove_saved_vacancy(vacancy_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "seeker":
        return error_response("NOT_AUTHORIZED", "Available only for seekers", 403)
        
    from app.models.seeker import SeekerProfile
    seeker_stmt = select(SeekerProfile.id).where(SeekerProfile.user_id == current_user.id)
    seeker_id = await db.scalar(seeker_stmt)
    
    checking_stmt = select(SavedVacancy).where(SavedVacancy.seeker_id == seeker_id, SavedVacancy.vacancy_id == vacancy_id)
    saved_vac = await db.scalar(checking_stmt)
    if not saved_vac:
        return error_response("NOT_SAVED", "Not in bookmarks", 404)

    await db.delete(saved_vac)
    await db.commit()
    return SuccessResponse(message="Removed from bookmarks")
