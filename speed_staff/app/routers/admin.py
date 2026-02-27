import uuid
from datetime import datetime as dt, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from itsdangerous import URLSafeTimedSerializer

from app.config import settings
from app.database import get_db

from app.models.user import User
from app.models.seeker import SeekerProfile, SeekerDocument, Skill
from app.models.employer import EmployerProfile
from app.models.vacancy import Vacancy
from app.models.application import Application
from app.models.review import Review, Report
from app.schemas.admin import (
    AdminPlatformStatsResponse, UserStats, VacancyStats, ApplicationStats, ReportStats, ReviewStats
)

from app.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/admin/templates")

# Admin Session Serializer
admin_serializer = URLSafeTimedSerializer(settings.ADMIN_SESSION_SECRET)

def get_admin_user(request: Request):
    """Dependency to check if admin is logged in via cookie"""
    cookie = request.cookies.get("admin_session")
    if not cookie:
        return None
    try:
        data = admin_serializer.loads(cookie, max_age=8 * 3600) # 8 hours
        if data.get("role") == "admin":
             return data
    except Exception:
        return None
    return None

async def admin_required(request: Request):
    user = get_admin_user(request)
    if not user:
         raise Exception("Unauthorized") # Captured carefully or we just redirect inside endpoint
    return user


# --- JSON API Endpoint ---
@router.get("/api/admin/stats", response_model=AdminPlatformStatsResponse)
async def get_admin_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        return JSONResponse(status_code=403, content={"error_code": "NOT_AUTHORIZED", "message": "Admin only"})

    users_total = await db.scalar(select(func.count(User.id))) or 0
    users_seekers = await db.scalar(select(func.count(User.id)).where(User.role == 'seeker')) or 0
    users_employers = await db.scalar(select(func.count(User.id)).where(User.role == 'employer')) or 0
    users_admins = await db.scalar(select(func.count(User.id)).where(User.role == 'admin')) or 0

    vac_active = await db.scalar(select(func.count(Vacancy.id)).where(Vacancy.status == 'active')) or 0
    vac_paused = await db.scalar(select(func.count(Vacancy.id)).where(Vacancy.status == 'paused')) or 0
    vac_closed = await db.scalar(select(func.count(Vacancy.id)).where(Vacancy.status == 'closed')) or 0

    app_total = await db.scalar(select(func.count(Application.id))) or 0
    today_start = dt.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    app_today = await db.scalar(select(func.count(Application.id)).where(Application.applied_at >= today_start)) or 0

    rep_pending = await db.scalar(select(func.count(Report.id)).where(Report.status == 'pending')) or 0
    rev_flagged = await db.scalar(select(func.count(Review.id)).where(Review.is_flagged == True)) or 0

    return AdminPlatformStatsResponse(
        users=UserStats(total=users_total, seekers=users_seekers, employers=users_employers, admins=users_admins),
        vacancies=VacancyStats(active=vac_active, paused=vac_paused, closed=vac_closed),
        applications=ApplicationStats(total=app_total, today=app_today),
        reports=ReportStats(pending=rep_pending),
        reviews=ReviewStats(flagged=rev_flagged)
    )


# --- HTML Admin Routes ---

@router.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_admin_user(request)
    if user:
         return RedirectResponse(url="/admin", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/admin/login")
async def process_login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
        session_data = {"username": username, "role": "admin"}
        cookie_value = admin_serializer.dumps(session_data)
        
        resp = RedirectResponse(url="/admin", status_code=302)
        resp.set_cookie(key="admin_session", value=cookie_value, httponly=True, max_age=8*3600)
        return resp
        
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})


@router.get("/admin/logout")
async def logout(response: Response):
    resp = RedirectResponse(url="/admin/login", status_code=302)
    resp.delete_cookie("admin_session")
    return resp


@router.get("/admin", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    # Fetch simple stats
    users_count = await db.scalar(select(func.count(User.id)))
    active_vacancies = await db.scalar(select(func.count(Vacancy.id)).where(Vacancy.status == 'active'))
    today_start = dt.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    apps_today = await db.scalar(select(func.count(Application.id)).where(Application.applied_at >= today_start))
    pending_reports = await db.scalar(select(func.count(Report.id)).where(Report.status == 'pending'))
    flagged_reviews = await db.scalar(select(func.count(Review.id)).where(Review.is_flagged == True))

    recent_users = (await db.execute(select(User).order_by(User.created_at.desc()).limit(10))).scalars().all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "admin_user": user,
        "users_count": users_count,
        "active_vacancies": active_vacancies,
        "apps_today": apps_today,
        "pending_reports": pending_reports,
        "flagged_reviews": flagged_reviews,
        "recent_users": recent_users
    })


@router.get("/admin/users", response_class=HTMLResponse)
async def list_users(request: Request, page: int = 1, limit: int = 20, db: AsyncSession = Depends(get_db)):
    user = get_admin_user(request)
    if not user: return RedirectResponse(url="/admin/login", status_code=302)

    offset = (page - 1) * limit
    users = (await db.execute(select(User).order_by(User.created_at.desc()).offset(offset).limit(limit))).scalars().all()
    return templates.TemplateResponse("users.html", {"request": request, "admin_user": user, "users": users, "page": page})


@router.get("/admin/users/{user_id}", response_class=HTMLResponse)
async def user_detail(request: Request, user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = get_admin_user(request)
    if not user: return RedirectResponse(url="/admin/login", status_code=302)

    db_user = await db.get(User, user_id)
    if not db_user:
        return HTMLResponse("User Not Found", status_code=404)

    profile = None
    if db_user.role == 'seeker':
        profile = await db.scalar(select(SeekerProfile).where(SeekerProfile.user_id == db_user.id))
    elif db_user.role == 'employer':
        profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == db_user.id))

    return templates.TemplateResponse("user_detail.html", {"request": request, "admin_user": user, "db_user": db_user, "profile": profile})


@router.post("/admin/users/{user_id}/block")
async def block_user(user_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    if not get_admin_user(request): return RedirectResponse(url="/admin/login", status_code=302)
    db_user = await db.get(User, user_id)
    if db_user:
        db_user.is_blocked = True
        await db.commit()
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=302)


@router.post("/admin/users/{user_id}/unblock")
async def unblock_user(user_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    if not get_admin_user(request): return RedirectResponse(url="/admin/login", status_code=302)
    db_user = await db.get(User, user_id)
    if db_user:
        db_user.is_blocked = False
        await db.commit()
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=302)


@router.post("/admin/employers/{user_id}/verify")
async def verify_employer(user_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    if not get_admin_user(request): return RedirectResponse(url="/admin/login", status_code=302)
    profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user_id))
    if profile:
        profile.is_verified = not profile.is_verified
        await db.commit()
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=302)


@router.get("/admin/vacancies", response_class=HTMLResponse)
async def list_vacancies(request: Request, page: int = 1, limit: int = 20, db: AsyncSession = Depends(get_db)):
    user = get_admin_user(request)
    if not user: return RedirectResponse(url="/admin/login", status_code=302)

    offset = (page - 1) * limit
    vacancies = (await db.execute(select(Vacancy).options(selectinload(Vacancy.employer)).order_by(Vacancy.created_at.desc()).offset(offset).limit(limit))).scalars().all()
    return templates.TemplateResponse("vacancies.html", {"request": request, "admin_user": user, "vacancies": vacancies, "page": page})
@router.get("/admin/applications", response_class=HTMLResponse)
async def list_applications(request: Request, page: int = 1, limit: int = 20, db: AsyncSession = Depends(get_db)):
    user = get_admin_user(request)
    if not user: return RedirectResponse(url="/admin/login", status_code=302)

    offset = (page - 1) * limit
    applications = (await db.execute(select(Application).options(
        selectinload(Application.vacancy).selectinload(Vacancy.employer),
        selectinload(Application.seeker).selectinload(SeekerProfile.user)
    ).order_by(Application.applied_at.desc()).offset(offset).limit(limit))).scalars().all()
    
    return templates.TemplateResponse("applications.html", {"request": request, "admin_user": user, "applications": applications, "page": page})

@router.get("/admin/reviews", response_class=HTMLResponse)
async def list_reviews(request: Request, page: int = 1, limit: int = 20, db: AsyncSession = Depends(get_db)):
    user = get_admin_user(request)
    if not user: return RedirectResponse(url="/admin/login", status_code=302)

    offset = (page - 1) * limit
    reviews = (await db.execute(select(Review).options(selectinload(Review.employer), selectinload(Review.author)).order_by(Review.is_flagged.desc(), Review.created_at.desc()).offset(offset).limit(limit))).scalars().all()
    return templates.TemplateResponse("reviews.html", {"request": request, "admin_user": user, "reviews": reviews, "page": page})


@router.get("/admin/reports", response_class=HTMLResponse)
async def list_reports(request: Request, page: int = 1, limit: int = 20, db: AsyncSession = Depends(get_db)):
    user = get_admin_user(request)
    if not user: return RedirectResponse(url="/admin/login", status_code=302)

    offset = (page - 1) * limit
    reports = (await db.execute(select(Report).options(selectinload(Report.reporter)).order_by(Report.created_at.desc()).offset(offset).limit(limit))).scalars().all()
    return templates.TemplateResponse("reports.html", {"request": request, "admin_user": user, "reports": reports, "page": page})


@router.post("/admin/reports/{report_id}/reviewed")
async def review_report(report_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    if not get_admin_user(request): return RedirectResponse(url="/admin/login", status_code=302)
    rep = await db.get(Report, report_id)
    if rep:
        rep.status = 'reviewed'
        await db.commit()
    return RedirectResponse(url="/admin/reports", status_code=302)


@router.get("/admin/documents", response_class=HTMLResponse)
async def list_documents(request: Request, page: int = 1, limit: int = 20, db: AsyncSession = Depends(get_db)):
    user = get_admin_user(request)
    if not user: return RedirectResponse(url="/admin/login", status_code=302)

    offset = (page - 1) * limit
    documents = (await db.execute(select(SeekerDocument).options(selectinload(SeekerDocument.seeker).selectinload(SeekerProfile.user)).where(SeekerDocument.is_verified == False).order_by(SeekerDocument.created_at.desc()).offset(offset).limit(limit))).scalars().all()
    return templates.TemplateResponse("documents.html", {"request": request, "admin_user": user, "documents": documents, "page": page})


@router.post("/admin/documents/{doc_id}/verify")
async def verify_document(doc_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    if not get_admin_user(request): return RedirectResponse(url="/admin/login", status_code=302)
    doc = await db.get(SeekerDocument, doc_id)
    if doc:
        doc.is_verified = True
        await db.commit()
    return RedirectResponse(url="/admin/documents", status_code=302)


@router.get("/admin/skills", response_class=HTMLResponse)
async def list_skills(request: Request, db: AsyncSession = Depends(get_db)):
    user = get_admin_user(request)
    if not user: return RedirectResponse(url="/admin/login", status_code=302)

    skills = (await db.execute(select(Skill).order_by(Skill.id.asc()))).scalars().all()
    return templates.TemplateResponse("skills.html", {"request": request, "admin_user": user, "skills": skills})


@router.post("/admin/skills")
async def create_skill(
    request: Request,
    name_uz: str = Form(...),
    name_ru: str = Form(""),
    name_en: str = Form(""),
    category: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    if not get_admin_user(request): return RedirectResponse(url="/admin/login", status_code=302)
    
    new_skill = Skill(
        name_uz=name_uz,
        name_ru=name_ru if name_ru else None,
        name_en=name_en if name_en else None,
        category=category
    )
    db.add(new_skill)
    await db.commit()
    return RedirectResponse(url="/admin/skills", status_code=302)


@router.post("/admin/skills/{skill_id}/delete")
async def delete_skill(skill_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    if not get_admin_user(request): return RedirectResponse(url="/admin/login", status_code=302)
    
    skill = await db.get(Skill, skill_id)
    if skill:
        await db.delete(skill)
        await db.commit()
    return RedirectResponse(url="/admin/skills", status_code=302)
