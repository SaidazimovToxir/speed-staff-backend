# Sprint 3 — Employer Profile Module

> Read `00_master.md` first.
> Auth done ✅ | Seeker done ✅ | Now: Employer Profile

---

## 1. WHAT TO BUILD

Employer (restaurant/cafe owner) profile system:
- Restaurant profile CRUD
- Public profile view for seekers and regular users
- Logo upload (already implemented in Sprint 2's upload router)

---

## 2. NEW FILES TO CREATE

```
app/
├── models/
│   └── employer.py        ← EmployerProfile
├── schemas/
│   └── employer.py
├── routers/
│   └── employer.py        ← /api/employer/*
└── services/
    └── employer_service.py
```

Add to `app/main.py`:
```python
from app.routers import employer
app.include_router(employer.router, prefix="/api/employer", tags=["Employer"])
```

---

## 3. DATABASE MODEL

### `app/models/employer.py`

**Table: `employer_profiles`**
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | default uuid4 |
| user_id | UUID FK → users.id | unique, cascade delete |
| restaurant_name | VARCHAR(200) | not null |
| description | TEXT | nullable |
| logo_url | VARCHAR(500) | nullable |
| city | VARCHAR(100) | nullable |
| district | VARCHAR(100) | nullable |
| address | VARCHAR(300) | nullable |
| phone | VARCHAR(20) | nullable |
| website | VARCHAR(300) | nullable |
| is_verified | BOOLEAN | default False — set by admin only |
| rating | DECIMAL(2,1) | default 0.0 — calculated from reviews |
| total_reviews | INTEGER | default 0 |
| created_at | TIMESTAMP TZ | default now() |
| updated_at | TIMESTAMP TZ | default now(), onupdate |

---

## 4. ALEMBIC MIGRATION

Create: `alembic/versions/003_employer_profile.py`

Creates `employer_profiles` table only.

---

## 5. SCHEMAS

### `app/schemas/employer.py`

Design schemas based on model. Rules:
- `EmployerProfileCreate` — restaurant_name required, rest optional
- `EmployerProfileUpdate` — all optional
- `EmployerProfileResponse` — full profile with rating, total_reviews, is_verified
- `EmployerProfileShortResponse` — compact for list views: id, restaurant_name, logo_url, city, rating, is_verified, total_reviews

---

## 6. ENDPOINTS

### `/api/employer`

---

**`POST /api/employer/profile`** — Create restaurant profile
- Auth: `employer` role required
- One user = one profile → `PROFILE_ALREADY_EXISTS` (409)
- Body: `EmployerProfileCreate`
- Returns: `EmployerProfileResponse`

---

**`GET /api/employer/profile`** — Get own profile
- Auth: `employer` required
- Returns: `EmployerProfileResponse`

---

**`PUT /api/employer/profile`** — Update own profile
- Auth: `employer` required
- Partial update
- Cannot update: `is_verified`, `rating`, `total_reviews` — these are system fields
- Body: `EmployerProfileUpdate`
- Returns: `EmployerProfileResponse`

---

**`GET /api/employer/profile/{employer_id}`** — Get any employer profile (public)
- Auth: none — public endpoint
- Returns: `EmployerProfileResponse`
- Used by seekers and regular users to view restaurant profile
- Error: `PROFILE_NOT_FOUND` (404)

---

**`GET /api/employer/dashboard`** — Employer dashboard stats
- Auth: `employer` required
- Returns custom response:
```json
{
  "active_vacancies": 3,
  "total_applications": 47,
  "new_applications_today": 5,
  "total_views": 1240,
  "profile_complete": true
}
```
- `profile_complete` = true if restaurant_name, city, phone, logo_url are all set
- Query vacancies and applications tables (they'll exist by Sprint 4 — implement this endpoint in Sprint 4 if needed, put placeholder now)

---

**`GET /api/employer/reviews`** — Get reviews for own restaurant
- Auth: `employer` required
- Returns: `PaginatedResponse[ReviewResponse]`
- Note: `ReviewResponse` defined in Sprint 6 — skip for now, implement in Sprint 6

---

## 7. ERROR CODES

| Code | Status | When |
|---|---|---|
| `PROFILE_NOT_FOUND` | 404 | Employer profile doesn't exist |
| `PROFILE_ALREADY_EXISTS` | 409 | Trying to create second profile |

---

## 8. NOTES FOR CURSOR

- `rating` and `total_reviews` fields must NEVER be updatable via the employer endpoints — they are updated only by the reviews system (Sprint 6)
- `is_verified` is updated only by admin (Sprint 7)
- Dashboard endpoint can return zeros/placeholders for Sprint 3, full logic in Sprint 4+
- Public profile endpoint (`GET /employer/profile/{id}`) should also include recent reviews in Sprint 6

---

*Sprint 3 complete → move to `04_vacancy.md`*
