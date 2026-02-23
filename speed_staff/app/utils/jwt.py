from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import HTTPException, status
from app.config import settings
from app.schemas.auth import TokenResponse

ALGORITHM = "HS256"

def create_access_token(user_id: str, role: str) -> str:
    """
    Payload: { sub: user_id, role: role, type: "access", exp: ... }
    Signed with SECRET_KEY using HS256
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(user_id), "role": role, "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_id: str) -> str:
    """
    Payload: { sub: user_id, type: "refresh", exp: ... }
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(user_id), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    """
    Decode and validate. Raise HTTPException 401 if invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error_code": "INVALID_TOKEN", "message": "Token is invalid or expired"},
        )

def create_token_pair(user_id: str, role: str) -> TokenResponse:
    """
    Create both tokens and return TokenResponse schema.
    """
    access_token = create_access_token(str(user_id), role)
    refresh_token = create_refresh_token(str(user_id))
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
