from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth_router
from app.schemas.common import ErrorDetail

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Speed Staff — restaurant staffing platform",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

@app.get("/", tags=["Info"])
async def root():
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "message": "Welcome to Speed Staff API"
    }

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorDetail(
            error_code="VALIDATION_ERROR",
            message="Pydantic validation failed",
            details=exc.errors()
        ).model_dump()
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ErrorDetail(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            details=str(exc) if settings.DEBUG else None
        ).model_dump()
    )

# HOW TO RUN
# 1. Create virtual environment
# python -m venv venv
# source venv/bin/activate  # Windows: venv\Scripts\activate
#
# 2. Install dependencies
# pip install -r requirements.txt
#
# 3. Copy and fill environment variables
# cp .env.example .env
#
# 4. Run database migrations
# alembic upgrade head
#
# 5. Start the server
# uvicorn app.main:app --reload --port 8000
#
# 6. Open Swagger UI
# http://localhost:8000/docs
