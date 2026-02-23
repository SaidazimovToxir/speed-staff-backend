# Sprint 2 — Seeker Profile Module

> Read `00_master.md` first.
> Implement everything in this file before moving to Sprint 3.

---

## 1. WHAT TO BUILD

Complete seeker (job seeker) profile system including:
- Profile CRUD
- Skills management
- Work experience
- Document/certificate uploads
- Resume upload
- File upload endpoint (shared, used by all future modules too)

---

## 2. NEW FILES TO CREATE

```
app/
├── models/
│   └── seeker.py          ← SeekerProfile, Skill, SeekerSkill, WorkExperience, SeekerDocument
├── schemas/
│   └── seeker.py          ← all seeker schemas
├── routers/
│   ├── seeker.py          ← /api/seeker/*
│   └── upload.py          ← /api/upload/*
└── services/
    └── seeker_service.py
```

Add to `app/main.py`:
```python
from app.routers import seeker, upload
app.include_router(seeker.router, prefix="/api/seeker", tags=["Seeker"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
```

Mount static files in `main.py`:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
```

---

## 3. DATABASE MODELS

### `app/models/seeker.py`

**Table: `seeker_profiles`**
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | default uuid4 |
| user_id | UUID FK → users.id | unique, cascade delete |
| first_name | VARCHAR(100) | not null |
| last_name | VARCHAR(100) | not null |
| middle_name | VARCHAR(100) | nullable |
| avatar_url | VARCHAR(500) | nullable |
| birth_date | DATE | nullable |
| gender | ENUM('male','female') | nullable |
| experience_years | SMALLINT | default 0 |
| city | VARCHAR(100) | nullable |
| district | VARCHAR(100) | nullable |
| expected_salary_min | INTEGER | nullable |
| expected_salary_max | INTEGER | nullable |
| bio | TEXT | nullable |
| is_available | BOOLEAN | default True |
| resume_url | VARCHAR(500) | nullable |
| rating | DECIMAL(2,1) | default 0.0 |
| total_reviews | INTEGER | default 0 |
| created_at | TIMESTAMP TZ | default now() |
| updated_at | TIMESTAMP TZ | default now(), onupdate |

**Table: `skills`** (reference/lookup table, seeded with data)
| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| name_uz | VARCHAR(100) | not null |
| name_ru | VARCHAR(100) | nullable |
| category | VARCHAR(50) | e.g. 'service', 'drinks', 'food', 'management' |

**Table: `seeker_skills`** (many-to-many)
| Column | Type | Notes |
|---|---|---|
| seeker_id | UUID FK → seeker_profiles.id | |
| skill_id | INTEGER FK → skills.id | |
| level | ENUM('beginner','intermediate','expert') | default 'beginner' |
| PK | (seeker_id, skill_id) | composite |

**Table: `work_experiences`**
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| seeker_id | UUID FK → seeker_profiles.id | cascade delete |
| company_name | VARCHAR(200) | not null |
| position | VARCHAR(100) | not null |
| start_date | DATE | not null |
| end_date | DATE | nullable — null means currently working |
| description | TEXT | nullable |
| created_at | TIMESTAMP TZ | default now() |

**Table: `seeker_documents`**
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| seeker_id | UUID FK → seeker_profiles.id | cascade delete |
| doc_type | ENUM('passport','certificate','diploma','other') | not null |
| title | VARCHAR(200) | not null |
| file_url | VARCHAR(500) | not null |
| is_verified | BOOLEAN | default False — set by admin only |
| created_at | TIMESTAMP TZ | default now() |

---

## 4. ALEMBIC MIGRATION

Create: `alembic/versions/002_seeker_profile.py`

Steps:
1. Create ENUM types: `gender_enum`, `skill_level_enum`, `doc_type_enum`
2. Create tables in order: `skills` → `seeker_profiles` → `seeker_skills` → `work_experiences` → `seeker_documents`
3. Seed `skills` table with initial data (insert in migration):

```python
skills_data = [
    # Service
    ("Xizmat ko'rsatish", "Обслуживание клиентов", "service"),
    ("Menyu bilish", "Знание меню", "service"),
    ("Buyurtma qabul qilish", "Приём заказов", "service"),
    ("Hisob-kitob qilish", "Расчёт клиентов", "service"),
    # Drinks
    ("Kofe tayyorlash", "Приготовление кофе", "drinks"),
    ("Kokteyl tayyorlash", "Приготовление коктейлей", "drinks"),
    ("Vino bilish", "Знание вин", "drinks"),
    # Food
    ("Issiq taomlar", "Горячие блюда", "food"),
    ("Sovuq taomlar", "Холодные блюда", "food"),
    ("Sushi", "Суши", "food"),
    ("Pizza", "Пицца", "food"),
    ("Milliy taomlar", "Национальные блюда", "food"),
    # Management
    ("Jamoa boshqarish", "Управление командой", "management"),
    ("Kassa", "Касса", "management"),
    ("Inventarizatsiya", "Инвентаризация", "management"),
]
```

---

## 5. SCHEMAS

### `app/schemas/seeker.py`

Design schemas yourself based on the models above. Follow these rules:
- Use `Optional` for nullable fields
- `SeekerProfileCreate` — fields required to create profile (first_name, last_name minimum)
- `SeekerProfileUpdate` — all fields optional (partial update)
- `SeekerProfileResponse` — full profile including skills list, experience count, rating
- `SeekerProfileShortResponse` — compact version for list views (id, name, avatar, position, rating, city, is_available)
- `WorkExperienceCreate` / `WorkExperienceResponse`
- `SeekerDocumentCreate` / `SeekerDocumentResponse`
- `SkillResponse` — id, name_uz, name_ru, category
- `AddSkillRequest` — skill_id + level
- `FileUploadResponse` — `{ "url": str }`

---

## 6. ENDPOINTS

### Seeker Profile — `/api/seeker`

---

**`POST /api/seeker/profile`** — Create profile
- Auth: `seeker` role required
- One user can only have one profile → `PROFILE_ALREADY_EXISTS` (409)
- Body: `SeekerProfileCreate`
- Returns: `SeekerProfileResponse`

---

**`GET /api/seeker/profile`** — Get own profile
- Auth: `seeker` required
- If no profile yet → `PROFILE_NOT_FOUND` (404)
- Returns: `SeekerProfileResponse` (full, with skills + experiences + documents)

---

**`PUT /api/seeker/profile`** — Update own profile
- Auth: `seeker` required
- Partial update — only update provided fields
- Body: `SeekerProfileUpdate`
- Returns: `SeekerProfileResponse`

---

**`GET /api/seeker/profile/{seeker_id}`** — Get any seeker profile (public)
- Auth: `employer` or `admin` only
- Returns: `SeekerProfileResponse`
- Error: `PROFILE_NOT_FOUND` (404)

---

**`GET /api/seeker/skills/all`** — Get all available skills
- Auth: none (public)
- Returns: `PaginatedResponse[SkillResponse]` grouped or flat — your choice
- Used to populate skill picker in mobile app

---

**`POST /api/seeker/skills`** — Add skill to own profile
- Auth: `seeker` required
- Body: `AddSkillRequest` (skill_id, level)
- Max 20 skills per seeker → `SKILLS_LIMIT_REACHED` (400)
- Duplicate skill → `SKILL_ALREADY_ADDED` (409)
- Returns: `SuccessResponse`

---

**`DELETE /api/seeker/skills/{skill_id}`** — Remove skill
- Auth: `seeker` required
- Returns: `SuccessResponse`

---

**`GET /api/seeker/experiences`** — List own work experiences
- Auth: `seeker` required
- Returns: list ordered by start_date desc

---

**`POST /api/seeker/experiences`** — Add work experience
- Auth: `seeker` required
- Validate: end_date must be after start_date if provided
- Max 10 experiences → `EXPERIENCES_LIMIT_REACHED` (400)
- Returns: `WorkExperienceResponse`

---

**`PUT /api/seeker/experiences/{exp_id}`** — Update experience
- Auth: `seeker`, must own the record
- Returns: `WorkExperienceResponse`

---

**`DELETE /api/seeker/experiences/{exp_id}`** — Delete experience
- Auth: `seeker`, must own the record
- Returns: `SuccessResponse`

---

**`GET /api/seeker/documents`** — List own documents
- Auth: `seeker` required
- Returns: list of `SeekerDocumentResponse`

---

**`DELETE /api/seeker/documents/{doc_id}`** — Delete document
- Auth: `seeker`, must own the record
- Returns: `SuccessResponse`

---

**`GET /api/seeker/saved-vacancies`** — List saved vacancies
- Auth: `seeker` required
- Returns: `PaginatedResponse[VacancyShortResponse]`
- Note: `VacancyShortResponse` will be defined in Sprint 4 — for now return raw dict or skip this endpoint and implement in Sprint 4

---

### File Upload — `/api/upload`

---

**`POST /api/upload/avatar`** — Upload profile picture
- Auth: any logged-in user
- Accept: `multipart/form-data`, field name `file`
- Allowed: jpg, jpeg, png, webp
- Max size: 5MB → `FILE_TOO_LARGE` (400)
- Wrong type → `INVALID_FILE_TYPE` (400)
- Save to: `./uploads/avatars/{uuid}.{ext}`
- Auto-resize image to max 800×800px (use Pillow)
- Returns: `FileUploadResponse { "url": "/uploads/avatars/uuid.jpg" }`
- After upload, caller should separately call `PUT /api/seeker/profile` with the new avatar_url

---

**`POST /api/upload/resume`** — Upload resume PDF
- Auth: `seeker` required
- Allowed: pdf only
- Max size: 10MB
- Save to: `./uploads/resumes/{uuid}.pdf`
- Returns: `FileUploadResponse`

---

**`POST /api/upload/document`** — Upload certificate or document
- Auth: `seeker` required
- Body (multipart): `file` + `doc_type` + `title`
- Allowed: pdf, jpg, jpeg, png
- Max size: 10MB
- Save to: `./uploads/documents/{uuid}.{ext}`
- Creates a `SeekerDocument` record in DB automatically
- Returns: `SeekerDocumentResponse`

---

**`POST /api/upload/logo`** — Upload restaurant logo
- Auth: `employer` required
- Allowed: jpg, jpeg, png, webp
- Max size: 5MB
- Save to: `./uploads/logos/{uuid}.{ext}`
- Auto-resize to max 400×400px
- Returns: `FileUploadResponse`

---

## 7. ERROR CODES FOR THIS MODULE

| Code | Status | When |
|---|---|---|
| `PROFILE_NOT_FOUND` | 404 | Seeker profile doesn't exist |
| `PROFILE_ALREADY_EXISTS` | 409 | Trying to create second profile |
| `SKILL_NOT_FOUND` | 404 | skill_id doesn't exist in skills table |
| `SKILL_ALREADY_ADDED` | 409 | Skill already on seeker's profile |
| `SKILLS_LIMIT_REACHED` | 400 | More than 20 skills |
| `EXPERIENCE_NOT_FOUND` | 404 | Work experience record not found |
| `EXPERIENCES_LIMIT_REACHED` | 400 | More than 10 experiences |
| `DOCUMENT_NOT_FOUND` | 404 | Document not found |
| `INVALID_DATE_RANGE` | 400 | end_date before start_date |
| `FILE_TOO_LARGE` | 400 | File exceeds size limit |
| `INVALID_FILE_TYPE` | 400 | Wrong file extension |
| `NOT_YOUR_RECORD` | 403 | Trying to edit another user's data |

---

## 8. NOTES FOR CURSOR

- Use `async` for all DB operations
- Use `select().options(selectinload(...))` for loading relations (skills, experiences) in one query
- For file operations use `aiofiles` for async file writing
- Image resizing: `from PIL import Image` — resize in memory before saving
- When deleting a document, also delete the physical file from disk
- `experience_years` on seeker profile should be calculated automatically from work_experiences, or let user set it manually — your choice, pick simpler approach
- All ownership checks: compare `record.seeker_id` with `current_user`'s seeker profile id

---

*Sprint 2 complete → move to `03_employer.md`*
