import uuid
from datetime import datetime as dt, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.application import Application
from app.models.vacancy import Vacancy
from app.models.seeker import SeekerProfile
from app.models.employer import EmployerProfile
from app.models.user import User

from app.schemas.application import (
    ApplicationCreate, ApplicationStatusUpdate, ApplicationResponse, ApplicationShortResponse
)
from app.schemas.common import ErrorDetail, SuccessResponse, PaginatedResponse, Meta
from app.dependencies import get_current_user

router = APIRouter()

def error_response(code: str, message: str, status_code: int, details=None):
    return JSONResponse(
        status_code=status_code,
        content=ErrorDetail(error_code=code, message=message, details=details).model_dump()
    )


@router.post("", response_model=ApplicationResponse | ErrorDetail)
async def submit_application(request: ApplicationCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "seeker":
        return error_response("NOT_AUTHORIZED", "Available only for seekers", 403)

    seeker_stmt = select(SeekerProfile).where(SeekerProfile.user_id == current_user.id)
    seeker = await db.scalar(seeker_stmt)
    if not seeker:
        return error_response("PROFILE_NOT_FOUND", "Create profile first", 404)

    vacancy = await db.get(Vacancy, request.vacancy_id)
    if not vacancy:
        return error_response("VACANCY_NOT_FOUND", "Vacancy not found", 404)
        
    if vacancy.status != 'active':
        return error_response("VACANCY_NOT_ACTIVE", "Vacancy is not active", 400)

    # Check duplicate
    dup_stmt = select(Application).where(Application.vacancy_id == request.vacancy_id, Application.seeker_id == seeker.id)
    if await db.scalar(dup_stmt):
        return error_response("ALREADY_APPLIED", "You have already applied", 409)

    app_record = Application(
        vacancy_id=vacancy.id,
        seeker_id=seeker.id,
        cover_letter=request.cover_letter
    )
    db.add(app_record)
    
    # Increment count
    vacancy.applications_count += 1
    
    await db.commit()
    await db.refresh(app_record)

    load_stmt = select(Application).options(
        selectinload(Application.vacancy).selectinload(Vacancy.employer),
        selectinload(Application.seeker)
    ).where(Application.id == app_record.id)
    
    res = await db.execute(load_stmt)
    loaded_app = res.scalars().first()

    return ApplicationResponse.model_validate(loaded_app)


@router.get("", response_model=PaginatedResponse[ApplicationShortResponse])
async def list_own_applications(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "seeker":
        return error_response("NOT_AUTHORIZED", "Only seekers can list their applications this way", 403)

    seeker_stmt = select(SeekerProfile.id).where(SeekerProfile.user_id == current_user.id)
    seeker_id = await db.scalar(seeker_stmt)
    if not seeker_id:
        return error_response("PROFILE_NOT_FOUND", "Profile not found", 404)

    stmt = select(Application).options(
        selectinload(Application.vacancy).selectinload(Vacancy.employer)
    ).where(Application.seeker_id == seeker_id)

    if status:
        stmt = stmt.where(Application.status == status)

    count_stmt = select(func.count(Application.id)).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.order_by(Application.applied_at.desc())
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    applications = result.scalars().all()

    pages = (total + limit - 1) // limit if total else 0
    meta = Meta(page=page, limit=limit, total=total, pages=pages, has_next=page < pages, has_prev=page > 1)

    return PaginatedResponse(items=[ApplicationShortResponse.model_validate(a) for a in applications], meta=meta)


@router.get("/{application_id}", response_model=ApplicationResponse | ErrorDetail)
async def get_application(application_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Application).options(
        selectinload(Application.vacancy).selectinload(Vacancy.employer),
        selectinload(Application.seeker)
    ).where(Application.id == application_id)
    
    result = await db.execute(stmt)
    application = result.scalars().first()

    if not application:
        return error_response("APPLICATION_NOT_FOUND", "Application not found", 404)

    is_seeker = current_user.role == "seeker" and application.seeker.user_id == current_user.id
    is_employer = current_user.role == "employer" and application.vacancy.employer.user_id == current_user.id
    is_admin = current_user.role == "admin"

    if not (is_seeker or is_employer or is_admin):
        return error_response("NOT_YOUR_RECORD", "Not authorized to view", 403)

    # Employer auto-view
    if is_employer and application.status == 'sent':
        application.status = 'viewed'
        application.viewed_at = dt.now(timezone.utc)
        await db.commit()
        await db.refresh(application)

    return ApplicationResponse.model_validate(application)


@router.patch("/{application_id}/status", response_model=ApplicationResponse | ErrorDetail)
async def update_application_status(
    application_id: uuid.UUID, 
    request: ApplicationStatusUpdate, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "employer":
        return error_response("NOT_AUTHORIZED", "Available only for employers", 403)

    stmt = select(Application).options(
        selectinload(Application.vacancy).selectinload(Vacancy.employer),
        selectinload(Application.seeker)
    ).where(Application.id == application_id)
    
    result = await db.execute(stmt)
    application = result.scalars().first()

    if not application:
        return error_response("APPLICATION_NOT_FOUND", "Application not found", 404)

    if application.vacancy.employer.user_id != current_user.id:
        return error_response("NOT_YOUR_RECORD", "Not your vacancy", 403)

    # Status transiton checks
    valid_transitions = {
        'sent': ['viewed', 'shortlisted', 'rejected'],
        'viewed': ['shortlisted', 'rejected'],
        'shortlisted': ['hired', 'rejected'],
        'rejected': [],
        'hired': []
    }

    if request.status not in valid_transitions.get(application.status, []):
        if application.status == 'rejected':
            return error_response("APPLICATION_ALREADY_REJECTED", "Cannot change rejected status", 400)
        if application.status == 'hired':
            return error_response("APPLICATION_ALREADY_HIRED", "Cannot change hired status", 400)
        return error_response("INVALID_STATUS_TRANSITION", f"Cannot move from {application.status} to {request.status}", 400)

    application.status = request.status
    if request.employer_note is not None:
        application.employer_note = request.employer_note

    if request.status == 'viewed' and not application.viewed_at:
         application.viewed_at = dt.now(timezone.utc)

    await db.commit()
    await db.refresh(application)

    return ApplicationResponse.model_validate(application)


@router.delete("/{application_id}", response_model=SuccessResponse | ErrorDetail)
async def withdraw_application(application_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "seeker":
        return error_response("NOT_AUTHORIZED", "Available only for seekers", 403)

    stmt = select(Application).where(Application.id == application_id)
    result = await db.execute(stmt)
    application = result.scalars().first()

    if not application:
        return error_response("APPLICATION_NOT_FOUND", "Application not found", 404)

    seeker_stmt = select(SeekerProfile.id).where(SeekerProfile.user_id == current_user.id)
    seeker_id = await db.scalar(seeker_stmt)

    if application.seeker_id != seeker_id:
         return error_response("NOT_YOUR_RECORD", "Not your application", 403)

    if application.status != 'sent':
        return error_response("CANNOT_WITHDRAW", "Application is already processed", 400)

    vacancy = await db.get(Vacancy, application.vacancy_id)
    if vacancy and vacancy.applications_count > 0:
        vacancy.applications_count -= 1

    await db.delete(application)
    await db.commit()

    return SuccessResponse(message="Application withdrawn successfully")
