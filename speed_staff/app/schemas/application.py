from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.schemas.vacancy import VacancyShortResponse
from app.schemas.seeker import SeekerProfileShortResponse

class ApplicationCreate(BaseModel):
    vacancy_id: UUID
    cover_letter: Optional[str] = None

class ApplicationStatusUpdate(BaseModel):
    status: str
    employer_note: Optional[str] = None

class ApplicationResponse(BaseModel):
    id: UUID
    status: str
    cover_letter: Optional[str] = None
    employer_note: Optional[str] = None
    applied_at: datetime
    viewed_at: Optional[datetime] = None
    
    vacancy: VacancyShortResponse
    seeker: SeekerProfileShortResponse

    model_config = {"from_attributes": True}

class ApplicationShortResponse(BaseModel):
    id: UUID
    status: str
    applied_at: datetime
    seeker: Optional[SeekerProfileShortResponse] = None
    vacancy: Optional[VacancyShortResponse] = None

    model_config = {"from_attributes": True}
