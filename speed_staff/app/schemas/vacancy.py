from datetime import datetime
from typing import Optional, List, Literal
from uuid import UUID
from pydantic import BaseModel

from app.schemas.seeker import SkillResponse
from app.schemas.employer import EmployerProfileShortResponse

class VacancySkillItem(BaseModel):
    skill_id: int
    is_required: bool = True

class VacancyCreate(BaseModel):
    title: str
    position: str
    description: str
    requirements: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_type: Literal['fixed', 'negotiable', 'hourly'] = "negotiable"
    experience_min: int = 0
    experience_max: Optional[int] = None
    work_type: Literal['fulltime', 'parttime', 'shift']
    schedule: Optional[str] = None

class VacancyUpdate(BaseModel):
    title: Optional[str] = None
    position: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_type: Optional[Literal['fixed', 'negotiable', 'hourly']] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    work_type: Optional[Literal['fulltime', 'parttime', 'shift']] = None
    schedule: Optional[str] = None

class VacancyStatusUpdate(BaseModel):
    status: Literal['active', 'paused', 'closed']

class VacancySkillResponse(BaseModel):
    skill: SkillResponse
    is_required: bool

    model_config = {"from_attributes": True}

class VacancyShortResponse(BaseModel):
    id: UUID
    title: str
    position: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_type: str
    work_type: str
    is_premium: bool
    status: str
    employer: EmployerProfileShortResponse
    created_at: datetime

    model_config = {"from_attributes": True}

class VacancyResponse(VacancyCreate):
    id: UUID
    employer_id: UUID
    status: str
    is_premium: bool
    premium_until: Optional[datetime] = None
    views_count: int
    applications_count: int
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    employer: EmployerProfileShortResponse
    skills: List[VacancySkillResponse] = []

    model_config = {"from_attributes": True}
