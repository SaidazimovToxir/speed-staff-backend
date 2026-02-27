from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel

class SkillResponse(BaseModel):
    id: int
    name_uz: str
    name_ru: Optional[str] = None
    name_en: Optional[str] = None
    category: str

    model_config = {"from_attributes": True}

class SeekerSkillResponse(BaseModel):
    skill: SkillResponse
    level: str

    model_config = {"from_attributes": True}

class WorkExperienceBase(BaseModel):
    company_name: str
    position: str
    start_date: date
    end_date: Optional[date] = None
    description: Optional[str] = None

class WorkExperienceCreate(WorkExperienceBase):
    pass

class WorkExperienceResponse(WorkExperienceBase):
    id: UUID
    seeker_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}

class SeekerDocumentBase(BaseModel):
    doc_type: str
    title: str

class SeekerDocumentCreate(SeekerDocumentBase):
    file_url: str

class SeekerDocumentResponse(SeekerDocumentBase):
    id: UUID
    seeker_id: UUID
    file_url: str
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class SeekerProfileCreate(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    avatar_url: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    experience_years: Optional[int] = 0
    city: Optional[str] = None
    district: Optional[str] = None
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    bio: Optional[str] = None
    is_available: Optional[bool] = True
    resume_url: Optional[str] = None

class SeekerProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    avatar_url: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    experience_years: Optional[int] = None
    city: Optional[str] = None
    district: Optional[str] = None
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    bio: Optional[str] = None
    is_available: Optional[bool] = None
    resume_url: Optional[str] = None

class SeekerProfileShortResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None
    position: Optional[str] = None # Derivated logic in controller
    rating: float
    city: Optional[str] = None
    is_available: bool

    model_config = {"from_attributes": True}

class SeekerProfileResponse(SeekerProfileCreate):
    id: UUID
    user_id: UUID
    avatar_url: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    experience_years: int
    city: Optional[str] = None
    district: Optional[str] = None
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    bio: Optional[str] = None
    is_available: bool
    resume_url: Optional[str] = None
    rating: float
    total_reviews: int
    created_at: datetime
    updated_at: datetime
    skills: List[SeekerSkillResponse] = []
    experiences: List[WorkExperienceResponse] = []
    documents: List[SeekerDocumentResponse] = []

    model_config = {"from_attributes": True}

class AddSkillRequest(BaseModel):
    skill_id: int
    level: str

class FileUploadResponse(BaseModel):
    url: str
