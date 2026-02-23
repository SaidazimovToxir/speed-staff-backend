import random
import re
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.database import get_db
from app.config import settings
from app.models.user import User, OTPCode
from app.schemas.auth import (
    SendOTPRequest, VerifyOTPRequest, RegisterWithEmailRequest,
    LoginWithEmailRequest, RefreshTokenRequest, ChangePasswordRequest,
    GoogleAuthRequest, TokenResponse, UserResponse, AuthResponse
)
from app.schemas.common import SuccessResponse, ErrorDetail
from app.utils.hashing import get_password_hash, verify_password
from app.utils.jwt import create_token_pair, decode_token
from app.services.otp_service import eskiz_service
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])

def validate_phone(phone: str) -> bool:
    return bool(re.match(r"^\+998\d{9}$", phone))

def error_response(code: str, message: str, status_code: int, details=None):
    return JSONResponse(
        status_code=status_code,
        content=ErrorDetail(error_code=code, message=message, details=details).model_dump()
    )

@router.post("/send-otp", response_model=SuccessResponse | ErrorDetail)
async def send_otp(request: SendOTPRequest, db: AsyncSession = Depends(get_db)):
    if not validate_phone(request.phone):
        return error_response("INVALID_PHONE_FORMAT", "Phone must be in +998XXXXXXXXX format", 400)
    
    stmt = select(OTPCode).where(
        OTPCode.phone == request.phone,
        OTPCode.purpose == request.purpose,
        OTPCode.is_used == False,
        OTPCode.expires_at > datetime.now(timezone.utc)
    ).order_by(OTPCode.created_at.desc())
    result = await db.execute(stmt)
    existing_otp = result.scalars().first()
    
    if existing_otp:
        retry_after = int((existing_otp.expires_at - datetime.now(timezone.utc)).total_seconds())
        return error_response("OTP_ALREADY_SENT", "OTP already sent", 429, details={"retry_after": retry_after})
    
    if settings.DEBUG:
        code = "111111"
    else:
        code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    
    new_otp = OTPCode(phone=request.phone, code=code, purpose=request.purpose, expires_at=expires_at)
    db.add(new_otp)
    await db.commit()
    
    success = await eskiz_service.send_otp(request.phone, code)
    if not success:
        return error_response("SMS_SEND_FAILED", "Eskiz API failed", 503)
    
    return SuccessResponse(message="OTP sent successfully" + (f", code: {code}" if settings.DEBUG else ""))

@router.post("/verify-otp", response_model=AuthResponse | SuccessResponse | ErrorDetail)
async def verify_otp(request: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(OTPCode).where(
        OTPCode.phone == request.phone,
        OTPCode.purpose == request.purpose,
        OTPCode.is_used == False
    ).order_by(OTPCode.created_at.desc())
    result = await db.execute(stmt)
    otp = result.scalars().first()
    
    if not otp:
        return error_response("OTP_NOT_FOUND", "No OTP found for phone+purpose", 404)
    if otp.expires_at < datetime.now(timezone.utc):
        return error_response("OTP_EXPIRED", "OTP exists but expired", 400)
    if otp.code != request.code:
        otp.attempts += 1
        if otp.attempts >= 5:
            otp.is_used = True
            await db.commit()
            return error_response("OTP_MAX_ATTEMPTS", "5 wrong attempts", 400)
        await db.commit()
        return error_response("OTP_INVALID", "Wrong code", 400)
    
    otp.is_used = True
    await db.commit()
    
    if request.purpose == 'register':
        stmt = select(User).where(User.phone == request.phone)
        result = await db.execute(stmt)
        if result.scalars().first():
            return error_response("USER_ALREADY_EXISTS", "Phone already registered", 409)
        
        user = User(phone=request.phone, is_verified=True, role=request.role or 'user')
        db.add(user)
        await db.commit()
        await db.refresh(user)
        tokens = create_token_pair(str(user.id), user.role)
        return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)
        
    elif request.purpose == 'login':
        stmt = select(User).where(User.phone == request.phone)
        result = await db.execute(stmt)
        user = result.scalars().first()
        if not user:
            return error_response("USER_NOT_FOUND", "No user with this phone", 404)
        if user.is_blocked:
            return error_response("USER_BLOCKED", "Admin blocked this user", 403)
        tokens = create_token_pair(str(user.id), user.role)
        return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)
        
    elif request.purpose == 'reset':
        return SuccessResponse(message="OTP verified")

@router.post("/register/email", response_model=AuthResponse | ErrorDetail)
async def register_email(request: RegisterWithEmailRequest, db: AsyncSession = Depends(get_db)):
    if len(request.password) < 8 or not any(c.isdigit() for c in request.password):
        return error_response("WEAK_PASSWORD", "Password doesn't meet requirements", 400)
    
    user_by_email = await db.execute(select(User).where(User.email == request.email))
    if user_by_email.scalars().first():
        return error_response("EMAIL_ALREADY_EXISTS", "Email already registered", 409)
        
    user_by_phone = await db.execute(select(User).where(User.phone == request.phone))
    if user_by_phone.scalars().first():
        return error_response("PHONE_ALREADY_EXISTS", "Phone already registered", 409)
        
    hashed_password = get_password_hash(request.password)
    user = User(
        phone=request.phone,
        email=request.email,
        password_hash=hashed_password,
        role=request.role,
        is_verified=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    tokens = create_token_pair(str(user.id), user.role)
    return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)

@router.post("/login/email", response_model=AuthResponse | ErrorDetail)
async def login_email(request: LoginWithEmailRequest, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).where(User.email == request.email))
    user = user_result.scalars().first()
    if not user:
        return error_response("USER_NOT_FOUND", "No user with this email", 404)
    if user.is_blocked:
        return error_response("USER_BLOCKED", "Admin blocked this user", 403)
    if not user.password_hash:
        return error_response("OAUTH_ACCOUNT", "User has no password", 400)
    if not verify_password(request.password, user.password_hash):
        return error_response("INVALID_CREDENTIALS", "Wrong password", 401)
        
    tokens = create_token_pair(str(user.id), user.role)
    return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)

@router.post("/google", response_model=AuthResponse | ErrorDetail)
async def google_auth(request: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    try:
        idinfo = id_token.verify_oauth2_token(
            request.id_token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError:
        return error_response("GOOGLE_TOKEN_INVALID", "Google ID token verification failed", 400)
        
    google_id = idinfo.get('sub')
    email = idinfo.get('email')
    
    user_result = await db.execute(select(User).where(User.google_id == google_id))
    user = user_result.scalars().first()
    
    if not user and email:
        user_result = await db.execute(select(User).where(User.email == email))
        user = user_result.scalars().first()
        if user:
            user.google_id = google_id
            await db.commit()
            
    if not user:
        user = User(
            phone=f"google_{google_id}",
            email=email,
            google_id=google_id,
            is_verified=True,
            role='user'
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
    if user.is_blocked:
        return error_response("USER_BLOCKED", "Admin blocked this user", 403)
        
    tokens = create_token_pair(str(user.id), user.role)
    return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)

@router.post("/refresh", response_model=TokenResponse | ErrorDetail)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(request.refresh_token)
    except Exception:
        return error_response("INVALID_TOKEN", "JWT invalid or expired", 401)
        
    if payload.get("type") != "refresh":
        return error_response("INVALID_TOKEN_TYPE", "Wrong token type", 400)
        
    user_id = payload.get("sub")
    user = await db.get(User, user_id)
    if not user:
        return error_response("USER_NOT_FOUND", "No user with this id", 404)
    if user.is_blocked:
        return error_response("USER_BLOCKED", "Admin blocked this user", 403)
        
    access_token = create_token_pair(str(user_id), user.role).access_token
    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/logout", response_model=SuccessResponse | ErrorDetail)
async def logout(current_user: User = Depends(get_current_user)):
    return SuccessResponse(message="Logged out successfully")

@router.post("/change-password", response_model=SuccessResponse | ErrorDetail)
async def change_password(request: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not current_user.password_hash:
        return error_response("OAUTH_ACCOUNT", "User has no password", 400)
    if not verify_password(request.old_password, current_user.password_hash):
        return error_response("INVALID_CREDENTIALS", "Wrong password", 401)
    if len(request.new_password) < 8 or not any(c.isdigit() for c in request.new_password):
        return error_response("WEAK_PASSWORD", "Password doesn't meet requirements", 400)
        
    current_user.password_hash = get_password_hash(request.new_password)
    await db.commit()
    return SuccessResponse(message="Password changed successfully")
