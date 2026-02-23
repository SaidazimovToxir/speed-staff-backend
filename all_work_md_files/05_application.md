# Sprint 5 — Applications Module

> Read `00_master.md` first.
> Auth ✅ | Seeker ✅ | Employer ✅ | Vacancies ✅ | Now: Applications

---

## 1. WHAT TO BUILD

Application system — seekers apply to vacancies, employers manage applications and update statuses.

---

## 2. NEW FILES TO CREATE

```
app/
├── models/
│   └── application.py     ← Application
├── schemas/
│   └── application.py
├── routers/
│   └── application.py     ← /api/applications/*
└── services/
    └── application_service.py
```

Add to `app/main.py`:
```python
from app.routers import application
app.include_router(application.router, prefix="/api/applications", tags=["Applications"])
```

---

## 3. DATABASE MODEL

**Table: `applications`**
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| vacancy_id | UUID FK → vacancies.id | cascade delete |
| seeker_id | UUID FK → seeker_profiles.id | cascade delete |
| cover_letter | TEXT | nullable |
| status | ENUM('sent','viewed','shortlisted','rejected','hired') | default 'sent' |
| employer_note | TEXT | nullable — visible to seeker |
| applied_at | TIMESTAMP TZ | default now() |
| viewed_at | TIMESTAMP TZ | nullable — set when employer opens it |
| updated_at | TIMESTAMP TZ | default now(), onupdate |
| UNIQUE | (vacancy_id, seeker_id) | one application per vacancy |

---

## 4. ALEMBIC MIGRATION

Create: `alembic/versions/005_applications.py`

Creates ENUM `application_status_enum` + `applications` table.
Add unique constraint on `(vacancy_id, seeker_id)`.
Add indexes: `ix_applications_seeker_id`, `ix_applications_vacancy_id`, `ix_applications_status`.

---

## 5. SCHEMAS

- `ApplicationCreate` — vacancy_id + optional cover_letter
- `ApplicationStatusUpdate` — `{ status, employer_note (optional) }`
- `ApplicationResponse` — full: id, status, cover_letter, employer_note, applied_at, viewed_at, vacancy (short), seeker (short)
- `ApplicationShortResponse` — compact for lists: id, status, applied_at, seeker short info (for employer view) OR vacancy short info (for seeker view)

---

## 6. ENDPOINTS

### `/api/applications`

---

**`POST /api/applications`** — Submit application
- Auth: `seeker` required, must have profile → `PROFILE_NOT_FOUND`
- Body: `ApplicationCreate`
- Validate vacancy exists and is active → `VACANCY_NOT_FOUND` / `VACANCY_NOT_ACTIVE` (400)
- Duplicate check → `ALREADY_APPLIED` (409)
- On success: increment `vacancies.applications_count` by 1
- Returns: `ApplicationResponse`

---

**`GET /api/applications`** — List own applications (seeker view)
- Auth: `seeker` required
- Query params: `status` filter, `page`, `limit`
- Returns: `PaginatedResponse[ApplicationShortResponse]` with vacancy info included

---

**`GET /api/applications/{application_id}`** — Get application detail
- Auth: `seeker` (own) or `employer` (their vacancy) or `admin`
- If employer opens it AND status is `sent` → auto-update status to `viewed`, set `viewed_at = now()`
- Returns: `ApplicationResponse`

---

**`PATCH /api/applications/{application_id}/status`** — Update application status
- Auth: `employer` only — must own the vacancy this application belongs to
- Body: `ApplicationStatusUpdate`
- Status transitions allowed:
  - `sent` → `viewed`, `shortlisted`, `rejected`
  - `viewed` → `shortlisted`, `rejected`
  - `shortlisted` → `hired`, `rejected`
  - `rejected` → no further changes → `APPLICATION_ALREADY_REJECTED` (400)
  - `hired` → no further changes → `APPLICATION_ALREADY_HIRED` (400)
- Returns: `ApplicationResponse`

---

**`DELETE /api/applications/{application_id}`** — Withdraw application
- Auth: `seeker` only, must own
- Only allowed if status is `sent` → `CANNOT_WITHDRAW` (400) if already viewed or further
- On delete: decrement `vacancies.applications_count` by 1 (min 0)
- Returns: `SuccessResponse`

---

### Also implement now (was placeholder in Sprint 4):

**`GET /api/vacancies/{vacancy_id}/applications`**
- Auth: `employer` (own vacancy) or `admin`
- Query params: `status` filter, `page`, `limit`
- Returns: `PaginatedResponse[ApplicationShortResponse]` with seeker info included

---

## 7. ERROR CODES

| Code | Status | When |
|---|---|---|
| `APPLICATION_NOT_FOUND` | 404 | Application doesn't exist |
| `ALREADY_APPLIED` | 409 | Seeker already applied to this vacancy |
| `VACANCY_NOT_ACTIVE` | 400 | Vacancy is paused or closed |
| `CANNOT_WITHDRAW` | 400 | Application already processed |
| `INVALID_STATUS_TRANSITION` | 400 | Status change not allowed |
| `APPLICATION_ALREADY_REJECTED` | 400 | Can't change rejected status |
| `APPLICATION_ALREADY_HIRED` | 400 | Can't change hired status |
| `NOT_YOUR_RECORD` | 403 | Not authorized to view/edit |

---

## 8. NOTES FOR CURSOR

- When employer calls `GET /api/applications/{id}`, auto-mark as viewed only if current user is the employer, not if it's the seeker viewing their own application
- `applications_count` on vacancy is a denormalized counter — keep it in sync on create and delete
- For the employer's application list, include seeker's name, avatar, rating, city, experience_years — enough to make a hiring decision from the list view
- For the seeker's application list, include vacancy title, employer name, logo, status, applied_at — enough to track their applications

---

*Sprint 5 complete → move to `06_review.md`*
