from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.utils.jwt import decode_token

security = HTTPBearer()
oauth2_scheme = security

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Decode JWT, get user from DB.
    Raise 401 if token invalid.
    Raise 403 if user is blocked.
    """
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error_code": "INVALID_TOKEN", "message": "Could not validate credentials"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error_code": "INVALID_TOKEN", "message": "Could not validate credentials"},
        )
    
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error_code": "USER_NOT_FOUND", "message": "User not found"},
        )
    
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "error_code": "USER_BLOCKED", "message": "User is blocked"},
        )
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Same as above but also checks is_active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "error_code": "USER_BLOCKED", "message": "User is inactive"},
        )
    return current_user

def require_role(*roles: str):
    """
    Factory that returns a dependency checking user role.
    Usage: Depends(require_role("admin", "employer"))
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "error_code": "INSUFFICIENT_PERMISSIONS", "message": "Not enough permissions"},
            )
        return current_user
    return role_checker
