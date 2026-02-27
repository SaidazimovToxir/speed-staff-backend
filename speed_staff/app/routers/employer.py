import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.employer import EmployerProfile
from app.models.user import User
from app.schemas.employer import (
    EmployerProfileCreate, EmployerProfileUpdate, EmployerProfileResponse, EmployerProfileShortResponse
)
from app.schemas.common import ErrorDetail, PaginatedResponse, Meta
from app.dependencies import get_current_user

router = APIRouter()

def error_response(code: str, message: str, status_code: int, details=None):
    return JSONResponse(
        status_code=status_code,
        content=ErrorDetail(error_code=code, message=message, details=details).model_dump()
    )


@router.post("/profile", response_model=EmployerProfileResponse | ErrorDetail)
async def create_profile(request: EmployerProfileCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "employer":
        return error_response("NOT_AUTHORIZED", "Available only for employers", 403)
        
    stmt = select(EmployerProfile).where(EmployerProfile.user_id == current_user.id)
    if await db.scalar(stmt):
        return error_response("PROFILE_ALREADY_EXISTS", "Profile already exists", 409)

    profile_data = request.model_dump()
    profile = EmployerProfile(**profile_data, user_id=current_user.id)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return EmployerProfileResponse.model_validate(profile)


@router.get("/profile", response_model=EmployerProfileResponse | ErrorDetail)
async def get_own_profile(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "employer":
        return error_response("NOT_AUTHORIZED", "Available only for employers", 403)

    stmt = select(EmployerProfile).where(EmployerProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        return error_response("PROFILE_NOT_FOUND", "Profile does not exist", 404)
        
    return EmployerProfileResponse.model_validate(profile)


@router.put("/profile", response_model=EmployerProfileResponse | ErrorDetail)
async def update_profile(request: EmployerProfileUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "employer":
        return error_response("NOT_AUTHORIZED", "Available only for employers", 403)

    stmt = select(EmployerProfile).where(EmployerProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        return error_response("PROFILE_NOT_FOUND", "Profile does not exist", 404)

    update_data = request.model_dump(exclude_unset=True)
    # The rating, total_reviews, is_verified are completely protected in the schema (not part of update schema) 
    # so they cannot be updated through this endpoint.
    
    for key, value in update_data.items():
        setattr(profile, key, value)
        
    await db.commit()
    await db.refresh(profile)
    
    return EmployerProfileResponse.model_validate(profile)


@router.get("/profile/{employer_id}", response_model=EmployerProfileResponse | ErrorDetail)
async def get_employer_profile(employer_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Public endpoint
    stmt = select(EmployerProfile).where(EmployerProfile.id == employer_id)
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        return error_response("PROFILE_NOT_FOUND", "Employer profile does not exist", 404)
        
    return EmployerProfileResponse.model_validate(profile)


from app.models.vacancy import Vacancy

from app.models.application import Application
from datetime import datetime as dt, timezone

@router.get("/dashboard")
async def get_dashboard_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "employer":
        return error_response("NOT_AUTHORIZED", "Available only for employers", 403)

    stmt = select(EmployerProfile).where(EmployerProfile.user_id == current_user.id)
    profile = await db.scalar(stmt)
    
    if not profile:
        return error_response("PROFILE_NOT_FOUND", "Profile does not exist", 404)

    is_complete = bool(profile.restaurant_name and profile.city and profile.phone and profile.logo_url)

    active_vacancies = await db.scalar(select(func.count(Vacancy.id)).where(Vacancy.employer_id == profile.id, Vacancy.status == 'active'))
    paused_vacancies = await db.scalar(select(func.count(Vacancy.id)).where(Vacancy.employer_id == profile.id, Vacancy.status == 'paused'))
    
    views_stmt = select(func.sum(Vacancy.views_count)).where(Vacancy.employer_id == profile.id)
    total_views = await db.scalar(views_stmt) or 0

    # Applications logic
    apps_stmt = select(func.count(Application.id)).join(Vacancy).where(Vacancy.employer_id == profile.id)
    total_apps = await db.scalar(apps_stmt) or 0

    today_start = dt.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    new_apps_stmt = select(func.count(Application.id)).join(Vacancy).where(Vacancy.employer_id == profile.id, Application.applied_at >= today_start)
    new_apps = await db.scalar(new_apps_stmt) or 0

    return {
        "active_vacancies": active_vacancies,
        "paused_vacancies": paused_vacancies,
        "total_applications": total_apps,
        "new_applications_today": new_apps,
        "total_views": total_views,
        "profile_complete": is_complete
    }


from app.models.review import Review
from app.schemas.review import ReviewResponse

@router.get("/reviews", response_model=PaginatedResponse[ReviewResponse])
async def get_employer_reviews(
    page: int = 1,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "employer":
        return error_response("NOT_AUTHORIZED", "Available only for employers", 403)

    stmt = select(EmployerProfile.id).where(EmployerProfile.user_id == current_user.id)
    employer_id = await db.scalar(stmt)
    if not employer_id:
        return error_response("PROFILE_NOT_FOUND", "Profile does not exist", 404)

    reviews_stmt = select(Review).options(
        selectinload(Review.author)
    ).where(Review.employer_id == employer_id, Review.is_visible == True)

    count_stmt = select(func.count(Review.id)).select_from(reviews_stmt.subquery())
    total = await db.scalar(count_stmt)

    reviews_stmt = reviews_stmt.order_by(Review.created_at.desc())
    offset = (page - 1) * limit
    reviews_stmt = reviews_stmt.offset(offset).limit(limit)

    result = await db.execute(reviews_stmt)
    reviews = result.scalars().all()

    pages = (total + limit - 1) // limit if total else 0
    meta = Meta(page=page, limit=limit, total=total, pages=pages, has_next=page < pages, has_prev=page > 1)

    return PaginatedResponse(items=[ReviewResponse.model_validate(r) for r in reviews], meta=meta)
