# Sprint 4 — Vacancies & Search Module

> Read `00_master.md` first.
> Auth ✅ | Seeker ✅ | Employer ✅ | Now: Vacancies + Search

---

## 1. WHAT TO BUILD

- Full vacancy CRUD for employers
- Vacancy listing and filtering for seekers
- Save/unsave vacancies
- Search endpoints for vacancies and seekers
- Premium vacancy flag (no payment yet — admin sets it manually for now)

---

## 2. NEW FILES TO CREATE

```
app/
├── models/
│   └── vacancy.py         ← Vacancy, VacancySkill, SavedVacancy
├── schemas/
│   └── vacancy.py
├── routers/
│   ├── vacancy.py         ← /api/vacancies/*
│   └── search.py          ← /api/search/*
└── services/
    └── vacancy_service.py
```

Add to `app/main.py`:
```python
from app.routers import vacancy, search
app.include_router(vacancy.router, prefix="/api/vacancies", tags=["Vacancies"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
```

---

## 3. DATABASE MODELS

### `app/models/vacancy.py`

**Table: `vacancies`**
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| employer_id | UUID FK → employer_profiles.id | cascade delete |
| title | VARCHAR(200) | not null |
| position | VARCHAR(100) | not null |
| description | TEXT | not null |
| requirements | TEXT | nullable |
| salary_min | INTEGER | nullable |
| salary_max | INTEGER | nullable |
| salary_type | ENUM('fixed','negotiable','hourly') | default 'negotiable' |
| experience_min | SMALLINT | default 0 |
| experience_max | SMALLINT | nullable |
| work_type | ENUM('fulltime','parttime','shift') | not null |
| schedule | VARCHAR(200) | nullable — e.g. "09:00–18:00, 5/2" |
| status | ENUM('active','paused','closed') | default 'active' |
| is_premium | BOOLEAN | default False |
| premium_until | TIMESTAMP TZ | nullable |
| views_count | INTEGER | default 0 |
| applications_count | INTEGER | default 0 |
| expires_at | TIMESTAMP TZ | nullable |
| created_at | TIMESTAMP TZ | default now() |
| updated_at | TIMESTAMP TZ | default now(), onupdate |

**Table: `vacancy_skills`** (many-to-many)
| Column | Type | Notes |
|---|---|---|
| vacancy_id | UUID FK → vacancies.id | cascade delete |
| skill_id | INTEGER FK → skills.id | |
| is_required | BOOLEAN | default True |
| PK | (vacancy_id, skill_id) | |

**Table: `saved_vacancies`** (many-to-many)
| Column | Type | Notes |
|---|---|---|
| seeker_id | UUID FK → seeker_profiles.id | cascade delete |
| vacancy_id | UUID FK → vacancies.id | cascade delete |
| saved_at | TIMESTAMP TZ | default now() |
| PK | (seeker_id, vacancy_id) | |

---

## 4. ALEMBIC MIGRATION

Create: `alembic/versions/004_vacancies.py`

Order: create ENUM types → `vacancies` → `vacancy_skills` → `saved_vacancies`

Add index: `ix_vacancies_status` on `vacancies.status`
Add index: `ix_vacancies_employer_id` on `vacancies.employer_id`

---

## 5. SCHEMAS

### `app/schemas/vacancy.py`

- `VacancyCreate` — all required fields for creation
- `VacancyUpdate` — all optional
- `VacancySkillItem` — `{ skill_id, is_required }`
- `VacancyResponse` — full vacancy with employer short info + skills list
- `VacancyShortResponse` — compact for list: id, title, position, salary_min, salary_max, work_type, is_premium, status, employer (name + logo + city + is_verified), created_at
- `VacancyStatusUpdate` — `{ status: 'active' | 'paused' | 'closed' }`

---

## 6. ENDPOINTS

### Vacancies — `/api/vacancies`

---

**`GET /api/vacancies`** — List active vacancies (public feed)
- Auth: none — public
- Only returns vacancies with `status = 'active'`
- Premium vacancies appear first (order by `is_premium DESC, created_at DESC`)
- Query params (all optional):
  - `position` (str) — filter by position (case-insensitive LIKE)
  - `salary_min` (int) — vacancy salary_max >= this value
  - `salary_max` (int) — vacancy salary_min <= this value
  - `experience_min` (int) — filter by experience_min >=
  - `experience_max` (int) — filter by experience_max <=
  - `work_type` (enum) — fulltime / parttime / shift
  - `skill_ids` (list[int]) — vacancies that require ANY of these skills
  - `city` (str) — filter by employer city
  - `page`, `limit`
- Returns: `PaginatedResponse[VacancyShortResponse]`

---

**`GET /api/vacancies/{vacancy_id}`** — Get vacancy detail
- Auth: none — public
- Increment `views_count` by 1 on each fetch (async, don't fail if this fails)
- Returns: `VacancyResponse` with full employer info and skills
- Error: `VACANCY_NOT_FOUND` (404)

---

**`POST /api/vacancies`** — Create vacancy
- Auth: `employer` required, must have profile → `PROFILE_NOT_FOUND`
- Body: `VacancyCreate` + optional `skills: list[VacancySkillItem]`
- Active vacancy limit without subscription: 3 → `VACANCY_LIMIT_REACHED` (400)
- Returns: `VacancyResponse`

---

**`PUT /api/vacancies/{vacancy_id}`** — Update vacancy
- Auth: `employer`, must own vacancy → `NOT_YOUR_RECORD` (403)
- Cannot edit if status is `closed` → `VACANCY_CLOSED` (400)
- Partial update
- Returns: `VacancyResponse`

---

**`PATCH /api/vacancies/{vacancy_id}/status`** — Change vacancy status
- Auth: `employer` (own) or `admin`
- Body: `VacancyStatusUpdate`
- Closed vacancies cannot be re-opened → `VACANCY_ALREADY_CLOSED` (400)
- Returns: `SuccessResponse`

---

**`DELETE /api/vacancies/{vacancy_id}`** — Delete vacancy
- Auth: `employer` (own) or `admin`
- Soft approach: set status to `closed` instead of hard delete, OR hard delete — your choice, pick simpler
- Returns: `SuccessResponse`

---

**`GET /api/vacancies/{vacancy_id}/applications`** — Get applications for a vacancy
- Auth: `employer` (must own vacancy) or `admin`
- Returns: `PaginatedResponse[ApplicationShortResponse]`
- Note: `ApplicationShortResponse` defined in Sprint 5 — implement this endpoint in Sprint 5

---

**`POST /api/vacancies/{vacancy_id}/save`** — Save vacancy to bookmarks
- Auth: `seeker` required
- Already saved → `ALREADY_SAVED` (409)
- Returns: `SuccessResponse`

---

**`DELETE /api/vacancies/{vacancy_id}/save`** — Remove from bookmarks
- Auth: `seeker` required
- Not saved → `NOT_SAVED` (404)
- Returns: `SuccessResponse`

---

**`GET /api/seeker/saved-vacancies`** — implement this now (was placeholder in Sprint 2)
- Auth: `seeker` required
- Returns: `PaginatedResponse[VacancyShortResponse]`
- Add this endpoint to the seeker router

---

### Search — `/api/search`

---

**`GET /api/search/vacancies`** — Search vacancies
- Same logic as `GET /api/vacancies` — can reuse the same service function
- Add `q` (str) query param — full text search on title + position + description
- Returns: `PaginatedResponse[VacancyShortResponse]`

---

**`GET /api/search/seekers`** — Search seeker profiles
- Auth: `employer` or `admin` required
- Query params (all optional):
  - `position` (str) — LIKE search on work_experiences.position
  - `salary_min` / `salary_max` — filter by expected_salary range
  - `experience_min` / `experience_max` — filter by experience_years
  - `skill_ids` (list[int]) — seekers who have ANY of these skills
  - `is_available` (bool) — filter by availability
  - `city` (str)
  - `page`, `limit`
- Returns: `PaginatedResponse[SeekerProfileShortResponse]`

---

**`GET /api/search/employers`** — Search restaurant profiles
- Auth: none — public
- Query params: `q` (name search), `city`, `is_verified`, `min_rating`, `page`, `limit`
- Returns: `PaginatedResponse[EmployerProfileShortResponse]`

---

**`GET /api/search/skills`** — Get all skills for picker
- Auth: none — public
- Query params: `q` (search by name), `category`
- Returns: list of `SkillResponse` (no pagination needed, skills list is small)

---

## 7. ALSO UPDATE IN THIS SPRINT

Update `GET /api/employer/dashboard` (added in Sprint 3 as placeholder):
```json
{
  "active_vacancies": 3,
  "paused_vacancies": 1,
  "total_applications": 47,
  "new_applications_today": 5,
  "total_views": 1240,
  "profile_complete": true
}
```
Now that vacancies table exists, implement the real queries.

---

## 8. ERROR CODES

| Code | Status | When |
|---|---|---|
| `VACANCY_NOT_FOUND` | 404 | Vacancy doesn't exist |
| `VACANCY_LIMIT_REACHED` | 400 | Too many active vacancies |
| `VACANCY_CLOSED` | 400 | Trying to edit closed vacancy |
| `VACANCY_ALREADY_CLOSED` | 400 | Trying to close already closed |
| `NOT_YOUR_RECORD` | 403 | Not the owner |
| `ALREADY_SAVED` | 409 | Vacancy already bookmarked |
| `NOT_SAVED` | 404 | Not in bookmarks |

---

## 9. NOTES FOR CURSOR

- `views_count` increment: use a background task or simple `UPDATE` — don't let it block the main response
- Skill filter: use `vacancy_skills` JOIN with `WHERE skill_id IN (...)` — at least one match is enough
- Premium vacancies: sort by `is_premium DESC` first, then `created_at DESC`
- For salary filter: if vacancy has no salary set (null), still include it in results — don't exclude nulls
- Free tier vacancy limit (3): count only `status = 'active'` vacancies, not paused or closed

---

*Sprint 4 complete → move to `05_application.md`*
