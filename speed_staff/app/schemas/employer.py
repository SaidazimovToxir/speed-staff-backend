from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

class EmployerProfileCreate(BaseModel):
    restaurant_name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    website: Optional[str] = None

class EmployerProfileUpdate(BaseModel):
    restaurant_name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    website: Optional[str] = None

class EmployerProfileShortResponse(BaseModel):
    id: UUID
    restaurant_name: str
    logo_url: Optional[str] = None
    city: Optional[str] = None
    rating: float
    is_verified: bool
    total_reviews: int

    model_config = {"from_attributes": True}

class EmployerProfileResponse(EmployerProfileCreate):
    id: UUID
    user_id: UUID
    is_verified: bool
    rating: float
    total_reviews: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
