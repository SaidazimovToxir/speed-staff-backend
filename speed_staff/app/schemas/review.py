from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, conint

from app.schemas.auth import UserResponse

class ReviewCreate(BaseModel):
    rating: conint(ge=1, le=5) # type: ignore
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: UUID
    rating: int
    comment: Optional[str] = None
    author: UserResponse
    created_at: datetime
    is_flagged: bool

    model_config = {"from_attributes": True}

class SeekerReviewCreate(ReviewCreate):
    pass

class SeekerReviewResponse(BaseModel):
    id: UUID
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    
    # We will include employer short info here so seekers know who rated them
    model_config = {"from_attributes": True}

class ReportCreate(BaseModel):
    target_type: str # 'vacancy', 'employer', 'seeker', 'review'
    target_id: UUID
    reason: str
    description: Optional[str] = None

class ReportResponse(ReportCreate):
    id: UUID
    reporter_id: UUID
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
