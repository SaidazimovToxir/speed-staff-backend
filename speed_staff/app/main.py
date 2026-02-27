from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

import os
from fastapi.staticfiles import StaticFiles

from fastapi.templating import Jinja2Templates

from app.config import settings
from app.routers import auth_router, seeker_router, upload_router, employer_router, vacancy_router, search_router, application_router, review_router, admin_router
from app.routers.location import router as location_router
from app.schemas.common import ErrorDetail
from app.utils.logger import logger

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

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

os.makedirs("app/admin/static", exist_ok=True)
app.mount("/admin/static", StaticFiles(directory="app/admin/static"), name="admin_static")

app.include_router(auth_router)
app.include_router(seeker_router, prefix="/api/seeker", tags=["Seeker"])
app.include_router(employer_router, prefix="/api/employer", tags=["Employer"])
app.include_router(vacancy_router, prefix="/api/vacancies", tags=["Vacancies"])
app.include_router(search_router, prefix="/api/search", tags=["Search"])
app.include_router(application_router, prefix="/api/applications", tags=["Applications"])
app.include_router(review_router, prefix="/api/reviews", tags=["Reviews"])
app.include_router(location_router)
app.include_router(admin_router, tags=["Admin"])
app.include_router(upload_router, prefix="/api/upload", tags=["Upload"])

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
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorDetail(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            details=str(exc) if settings.DEBUG else None
        ).model_dump()
    )

# HOW TO RUN LOCALLY (STANDARD)
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
#
# ----------------------------------------
# HOW TO RUN VIA DOCKER (RECOMMENDED)
# 1. Create virtual environment (optional but good for IDEs)
# python -m venv venv
# source venv/bin/activate  # Windows: venv\Scripts\activate
#
# 2. Make sure you have Docker Desktop installed and running
#
# 3. Build and string up containers in the background
# docker compose up --build -d
#
# 4. View API Logs (to check if it started and migrated successfully)
# docker logs speed_staff_api
#
# 5. Open Swagger UI (Notice Port 8080! It goes through the NGINX proxy)
# http://localhost:8080/docs
# 
# 6. Stop containers
# docker compose down
