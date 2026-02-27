from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr

class SendOTPRequest(BaseModel):
    phone: str

class VerifyOTPRequest(BaseModel):
    phone: str
    code: str

class FinalizeRegistrationRequest(BaseModel):
    phone: str
    code: str
    password: str
    role: Literal['seeker', 'employer']
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    restaurant_name: Optional[str] = None

class RegisterWithEmailRequest(BaseModel):
    email: EmailStr
    password: str
    role: Literal['seeker', 'employer', 'user']
    phone: str

class LoginWithEmailRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class GoogleAuthRequest(BaseModel):
    id_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserResponse(BaseModel):
    id: UUID
    phone: str
    email: Optional[str] = None
    role: str
    is_verified: bool
    is_blocked: bool
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse
