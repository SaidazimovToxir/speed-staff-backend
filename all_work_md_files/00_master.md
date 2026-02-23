# Speed Staff — Master Technical Specification
> This is the main overview document. Each module has its own detailed spec file.
> Read this first before opening any module spec.

---

## 1. PROJECT SUMMARY

**Speed Staff** is a mobile platform (Android/iOS) connecting restaurant workers with employers in Uzbekistan.

**Backend:** FastAPI (Python 3.11+, async)  
**Database:** PostgreSQL (SQLAlchemy 2.0 async + asyncpg)  
**Auth:** Already implemented — JWT (access/refresh) + SMS OTP via Eskiz.uz  
**File Storage:** Local filesystem (`./uploads/`)  
**API Docs:** Swagger UI at `/docs`  
**Admin Panel:** FastAPI + Jinja2 HTML templates at `/admin`

---

## 2. USER ROLES

| Role | Value | Description |
|---|---|---|
| Job Seeker | `seeker` | Restaurant worker looking for jobs |
| Employer | `employer` | Restaurant/cafe owner or HR manager |
| Regular User | `user` | Browses restaurants, leaves reviews |
| Admin | `admin` | Platform moderator, full access |

---

## 3. CURRENT STATE (already done)

Auth module is fully implemented and working:
- `POST /api/auth/send-otp`
- `POST /api/auth/verify-otp`
- `POST /api/auth/register/email`
- `POST /api/auth/login/email`
- `POST /api/auth/google`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/auth/change-password`

Existing files and structure:
```
app/
├── main.py
├── config.py
├── database.py
├── dependencies.py          ← get_current_user, require_role() are ready
├── models/user.py           ← User, OTPCode models exist
├── schemas/common.py        ← SuccessResponse, ErrorDetail, PaginatedResponse[T], Meta
├── schemas/auth.py
├── routers/auth.py
├── services/auth_service.py
├── services/otp_service.py
└── utils/jwt.py, hashing.py, responses.py
```

**Do not modify auth files unless a module explicitly requires it.**

---

## 4. DATABASE — ALL TABLES OVERVIEW

All tables are already designed. Migrations should be added incrementally per module.

```
users                  ← exists
otp_codes              ← exists
─────────────────────────────────
seeker_profiles        ← Sprint 2
skills                 ← Sprint 2
seeker_skills          ← Sprint 2
work_experiences       ← Sprint 2
seeker_documents       ← Sprint 2
─────────────────────────────────
employer_profiles      ← Sprint 3
─────────────────────────────────
vacancies              ← Sprint 4
vacancy_skills         ← Sprint 4
saved_vacancies        ← Sprint 4
─────────────────────────────────
applications           ← Sprint 5
─────────────────────────────────
reviews                ← Sprint 6
seeker_reviews         ← Sprint 6
reports                ← Sprint 6
─────────────────────────────────
subscriptions          ← Sprint 7 (Admin)
payments               ← Sprint 7 (Admin)
```

---

## 5. SPRINT ORDER

Implement modules in this exact order. Do not skip ahead.

| Sprint | Module | Spec File |
|---|---|---|
| ✅ Sprint 1 | Auth | Done |
| Sprint 2 | Seeker Profile | `02_seeker.md` |
| Sprint 3 | Employer Profile | `03_employer.md` |
| Sprint 4 | Vacancies & Search | `04_vacancy.md` |
| Sprint 5 | Applications | `05_application.md` |
| Sprint 6 | Reviews & Reports | `06_review.md` |
| Sprint 7 | Admin Panel | `07_admin.md` |

---

## 6. GLOBAL CONVENTIONS

### Response format
Every endpoint must return one of these schemas from `schemas/common.py`:
- `SuccessResponse` — simple success
- `ErrorDetail` — all errors
- `PaginatedResponse[T]` — all lists
- Custom response schema — for data responses

### Error format
```json
{
  "success": false,
  "error_code": "SNAKE_CASE_CODE",
  "message": "Human readable message",
  "details": null
}
```

### Pagination
All list endpoints accept `?page=1&limit=20` query params.
Return `PaginatedResponse[T]` with `meta` containing `page, limit, total, pages, has_next, has_prev`.

### File uploads
- Endpoint: `POST /api/upload/{type}` — already planned, implement in Sprint 2
- Files saved to `./uploads/{type}/{uuid}.{ext}`
- Return: `{ "url": "/uploads/avatars/abc123.jpg" }`
- Serve static files via FastAPI `StaticFiles` mounted at `/uploads`

### Authentication header
```
Authorization: Bearer <access_token>
```

### Role enforcement
Use `require_role()` dependency from `dependencies.py`:
```python
@router.get("/", dependencies=[Depends(require_role("employer", "admin"))])
```

### Swagger tags
Each router must declare its tag. Use these exact tag names:
- `Seeker` `Employer` `Vacancies` `Applications` `Reviews` `Upload` `Admin`

---

## 7. ENVIRONMENT (already set in .env)

No new env variables needed until Sprint 7 (Admin panel secret).

---

## 8. HOW TO USE THESE SPECS

1. Open the sprint spec file (e.g. `02_seeker.md`)
2. Read the full spec before writing any code
3. Implement in this order per sprint:
   - Alembic migration first
   - Models
   - Schemas
   - Service layer (business logic)
   - Router (endpoints)
   - Wire router into `main.py`
4. Test via Swagger at `/docs` before moving to next sprint
5. Never break existing auth endpoints

---

*Speed Staff Backend — Master Spec v1.0*
