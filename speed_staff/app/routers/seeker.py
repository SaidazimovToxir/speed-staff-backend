import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.seeker import SeekerProfile, Skill, SeekerSkill, WorkExperience, SeekerDocument
from app.models.user import User
from app.schemas.seeker import (
    SeekerProfileCreate, SeekerProfileUpdate, SeekerProfileResponse, SeekerProfileShortResponse,
    SkillResponse, AddSkillRequest, WorkExperienceCreate, WorkExperienceResponse,
    SeekerDocumentResponse
)
from app.schemas.common import ErrorDetail, SuccessResponse, PaginatedResponse, Meta
from app.dependencies import get_current_user

router = APIRouter()

def error_response(code: str, message: str, status_code: int, details=None):
    return JSONResponse(
        status_code=status_code,
        content=ErrorDetail(error_code=code, message=message, details=details).model_dump()
    )

# --- Profil yaratish va tahrirlash ---

@router.post("/profile", response_model=SeekerProfileResponse | ErrorDetail)
async def create_profile(request: SeekerProfileCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "seeker":
        return error_response("NOT_AUTHORIZED", "Available only for seekers", 403)
        
    stmt = select(SeekerProfile).where(SeekerProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    if result.scalars().first():
        return error_response("PROFILE_ALREADY_EXISTS", "Profile already exists", 409)

    profile_data = request.model_dump()
    profile = SeekerProfile(**profile_data, user_id=current_user.id)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    stmt = select(SeekerProfile).options(
        selectinload(SeekerProfile.skills).selectinload(SeekerSkill.skill),
        selectinload(SeekerProfile.experiences),
        selectinload(SeekerProfile.documents)
    ).where(SeekerProfile.id == profile.id)
    
    res = await db.execute(stmt)
    loaded_profile = res.scalars().first()
    
    return SeekerProfileResponse.model_validate(loaded_profile)

@router.get("/profile", response_model=SeekerProfileResponse | ErrorDetail)
async def get_own_profile(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "seeker":
        return error_response("NOT_AUTHORIZED", "Available only for seekers", 403)

    stmt = select(SeekerProfile).options(
        selectinload(SeekerProfile.skills).selectinload(SeekerSkill.skill),
        selectinload(SeekerProfile.experiences),
        selectinload(SeekerProfile.documents)
    ).where(SeekerProfile.user_id == current_user.id)
    
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        return error_response("PROFILE_NOT_FOUND", "Profile does not exist", 404)
        
    return SeekerProfileResponse.model_validate(profile)

@router.put("/profile", response_model=SeekerProfileResponse | ErrorDetail)
async def update_profile(request: SeekerProfileUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "seeker":
        return error_response("NOT_AUTHORIZED", "Available only for seekers", 403)

    stmt = select(SeekerProfile).where(SeekerProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        return error_response("PROFILE_NOT_FOUND", "Profile does not exist", 404)

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
        
    await db.commit()
    
    stmt_load = select(SeekerProfile).options(
        selectinload(SeekerProfile.skills).selectinload(SeekerSkill.skill),
        selectinload(SeekerProfile.experiences),
        selectinload(SeekerProfile.documents)
    ).where(SeekerProfile.user_id == current_user.id)
    
    res = await db.execute(stmt_load)
    loaded_profile = res.scalars().first()
    
    return SeekerProfileResponse.model_validate(loaded_profile)

@router.get("/profile/{seeker_id}", response_model=SeekerProfileResponse | ErrorDetail)
async def get_seeker_profile(seeker_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role not in ["employer", "admin"]:
        return error_response("NOT_AUTHORIZED", "Only employers or admins can view full profiles by id", 403)

    stmt = select(SeekerProfile).options(
        selectinload(SeekerProfile.skills).selectinload(SeekerSkill.skill),
        selectinload(SeekerProfile.experiences),
        selectinload(SeekerProfile.documents)
    ).where(SeekerProfile.id == seeker_id)
    
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        return error_response("PROFILE_NOT_FOUND", "Profile does not exist", 404)
        
    return SeekerProfileResponse.model_validate(profile)

# --- Skills (Ko'nikmalar) ---

@router.get("/skills/all", response_model=PaginatedResponse[SkillResponse])
async def get_all_skills(page: int = 1, limit: int = 50, db: AsyncSession = Depends(get_db)):
    offset = (page - 1) * limit
    
    count_stmt = select(func.count(Skill.id))
    total = await db.scalar(count_stmt)
    
    stmt = select(Skill).offset(offset).limit(limit)
    result = await db.execute(stmt)
    skills = result.scalars().all()
    
    pages = (total + limit - 1) // limit
    
    meta = Meta(
        page=page, limit=limit, total=total, pages=pages,
        has_next=page < pages, has_prev=page > 1
    )
    
    return PaginatedResponse(items=[SkillResponse.model_validate(s) for s in skills], meta=meta)

@router.post("/skills", response_model=SuccessResponse | ErrorDetail)
async def add_skill_to_profile(request: AddSkillRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "seeker":
        return error_response("NOT_AUTHORIZED", "Available only for seekers", 403)
        
    profile_stmt = select(SeekerProfile.id).where(SeekerProfile.user_id == current_user.id)
    profile_id = await db.scalar(profile_stmt)
    if not profile_id:
         return error_response("PROFILE_NOT_FOUND", "Create profile first", 404)

    skill = await db.get(Skill, request.skill_id)
    if not skill:
        return error_response("SKILL_NOT_FOUND", "Skill not found in database", 404)

    count_stmt = select(func.count(SeekerSkill.skill_id)).where(SeekerSkill.seeker_id == profile_id)
    skill_count = await db.scalar(count_stmt)
    
    if skill_count >= 20:
        return error_response("SKILLS_LIMIT_REACHED", "Max 20 skills allowed", 400)

    existing_stmt = select(SeekerSkill).where(SeekerSkill.seeker_id == profile_id, SeekerSkill.skill_id == request.skill_id)
    if await db.scalar(existing_stmt):
        return error_response("SKILL_ALREADY_ADDED", "Skill already on profile", 409)

    new_skill = SeekerSkill(seeker_id=profile_id, skill_id=request.skill_id, level=request.level)
    db.add(new_skill)
    await db.commit()
    
    return SuccessResponse(message="Skill added to profile")

@router.delete("/skills/{skill_id}", response_model=SuccessResponse | ErrorDetail)
async def remove_skill(skill_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile_stmt = select(SeekerProfile.id).where(SeekerProfile.user_id == current_user.id)
    profile_id = await db.scalar(profile_stmt)
    if not profile_id:
         return error_response("PROFILE_NOT_FOUND", "Create profile first", 404)

    stmt = select(SeekerSkill).where(SeekerSkill.seeker_id == profile_id, SeekerSkill.skill_id == skill_id)
    result = await db.execute(stmt)
    seeker_skill = result.scalars().first()
    
    if not seeker_skill:
        return error_response("NOT_YOUR_RECORD", "Skill not found on your profile", 403)

    await db.delete(seeker_skill)
    await db.commit()
    
    return SuccessResponse(message="Skill removed")

# --- Work Experiences ---

@router.get("/experiences", response_model=List[WorkExperienceResponse] | ErrorDetail)
async def list_experiences(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "seeker":
        return error_response("NOT_AUTHORIZED", "Available only for seekers", 403)
        
    profile_stmt = select(SeekerProfile.id).where(SeekerProfile.user_id == current_user.id)
    profile_id = await db.scalar(profile_stmt)
    if not profile_id:
         return error_response("PROFILE_NOT_FOUND", "Create profile first", 404)

    stmt = select(WorkExperience).where(WorkExperience.seeker_id == profile_id).order_by(WorkExperience.start_date.desc())
    result = await db.execute(stmt)
    experiences = result.scalars().all()
    
    return [WorkExperienceResponse.model_validate(e) for e in experiences]

@router.post("/experiences", response_model=WorkExperienceResponse | ErrorDetail)
async def add_experience(request: WorkExperienceCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "seeker":
         return error_response("NOT_AUTHORIZED", "Available only for seekers", 403)

    if request.end_date and request.end_date < request.start_date:
        return error_response("INVALID_DATE_RANGE", "End date must be after start date", 400)

    profile_stmt = select(SeekerProfile.id).where(SeekerProfile.user_id == current_user.id)
    profile_id = await db.scalar(profile_stmt)
    if not profile_id:
         return error_response("PROFILE_NOT_FOUND", "Create profile first", 404)

    count_stmt = select(func.count(WorkExperience.id)).where(WorkExperience.seeker_id == profile_id)
    if await db.scalar(count_stmt) >= 10:
        return error_response("EXPERIENCES_LIMIT_REACHED", "Max 10 experiences allowed", 400)

    exp_data = request.model_dump()
    exp = WorkExperience(**exp_data, seeker_id=profile_id)
    db.add(exp)
    await db.commit()
    await db.refresh(exp)

    return WorkExperienceResponse.model_validate(exp)

@router.put("/experiences/{exp_id}", response_model=WorkExperienceResponse | ErrorDetail)
async def update_experience(exp_id: uuid.UUID, request: WorkExperienceCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile_stmt = select(SeekerProfile.id).where(SeekerProfile.user_id == current_user.id)
    profile_id = await db.scalar(profile_stmt)
    
    exp = await db.get(WorkExperience, exp_id)
    if not exp or exp.seeker_id != profile_id:
        return error_response("NOT_YOUR_RECORD", "Experience not found or not yours", 403)

    if request.end_date and request.end_date < request.start_date:
        return error_response("INVALID_DATE_RANGE", "End date must be after start date", 400)

    update_data = request.model_dump()
    for k, v in update_data.items():
        setattr(exp, k, v)
        
    await db.commit()
    await db.refresh(exp)
    return WorkExperienceResponse.model_validate(exp)

@router.delete("/experiences/{exp_id}", response_model=SuccessResponse | ErrorDetail)
async def delete_experience(exp_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile_stmt = select(SeekerProfile.id).where(SeekerProfile.user_id == current_user.id)
    profile_id = await db.scalar(profile_stmt)
    
    exp = await db.get(WorkExperience, exp_id)
    if not exp or exp.seeker_id != profile_id:
        return error_response("NOT_YOUR_RECORD", "Experience not found or not yours", 403)

    await db.delete(exp)
    await db.commit()
    return SuccessResponse(message="Experience deleted")

# --- Documents ---

@router.get("/documents", response_model=List[SeekerDocumentResponse] | ErrorDetail)
async def list_documents(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile_stmt = select(SeekerProfile.id).where(SeekerProfile.user_id == current_user.id)
    profile_id = await db.scalar(profile_stmt)
    if not profile_id:
         return error_response("PROFILE_NOT_FOUND", "Create profile first", 404)

    stmt = select(SeekerDocument).where(SeekerDocument.seeker_id == profile_id)
    result = await db.execute(stmt)
    docs = result.scalars().all()
    
    return [SeekerDocumentResponse.model_validate(d) for d in docs]

@router.delete("/documents/{doc_id}", response_model=SuccessResponse | ErrorDetail)
async def delete_document(doc_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile_stmt = select(SeekerProfile.id).where(SeekerProfile.user_id == current_user.id)
    profile_id = await db.scalar(profile_stmt)
    
    doc = await db.get(SeekerDocument, doc_id)
    if not doc or doc.seeker_id != profile_id:
        return error_response("NOT_YOUR_RECORD", "Document not found or not yours", 403)

    import os
    if os.path.exists(doc.file_url.lstrip('/')):
        os.remove(doc.file_url.lstrip('/'))

    await db.delete(doc)
    await db.commit()
from app.models.vacancy import SavedVacancy, Vacancy
from app.schemas.vacancy import VacancyShortResponse

@router.get("/saved-vacancies", response_model=PaginatedResponse[VacancyShortResponse] | ErrorDetail)
async def list_saved_vacancies(
    page: int = 1,
    limit: int = 50,
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "seeker":
        return error_response("NOT_AUTHORIZED", "Available only for seekers", 403)
        
    profile_stmt = select(SeekerProfile.id).where(SeekerProfile.user_id == current_user.id)
    profile_id = await db.scalar(profile_stmt)
    if not profile_id:
         return error_response("PROFILE_NOT_FOUND", "Create profile first", 404)

    stmt = select(Vacancy).join(SavedVacancy, Vacancy.id == SavedVacancy.vacancy_id).options(
        selectinload(Vacancy.employer)
    ).where(SavedVacancy.seeker_id == profile_id)

    count_stmt = select(func.count(Vacancy.id)).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.order_by(SavedVacancy.saved_at.desc())
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    vacancies = result.scalars().unique().all()
    
    pages = (total + limit - 1) // limit if total else 0
    meta = Meta(page=page, limit=limit, total=total, pages=pages, has_next=page < pages, has_prev=page > 1)
    
    return PaginatedResponse(items=[VacancyShortResponse.model_validate(v) for v in vacancies], meta=meta)
