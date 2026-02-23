from typing import Generic, TypeVar, List, Optional, Any
from pydantic import BaseModel

T = TypeVar('T')

class Meta(BaseModel):
    """Pagination metadata"""
    page: int
    limit: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list response"""
    items: List[T]
    meta: Meta

class SuccessResponse(BaseModel):
    """Simple success message"""
    success: bool = True
    message: str

class ErrorDetail(BaseModel):
    """Standard error response"""
    success: bool = False
    error_code: str
    message: str
    details: Optional[Any] = None
