# Sprint 6 — Reviews & Reports Module

> Read `00_master.md` first.
> Auth ✅ | Seeker ✅ | Employer ✅ | Vacancies ✅ | Applications ✅ | Now: Reviews + Reports

---

## 1. WHAT TO BUILD

- Restaurant reviews (any logged-in user can review an employer)
- Seeker ratings (only employers who have hired a seeker can rate them)
- Report system (flag content for admin review)
- Auto-update employer and seeker rating averages

---

## 2. NEW FILES TO CREATE

```
app/
├── models/
│   └── review.py          ← Review, SeekerReview, Report
├── schemas/
│   └── review.py
├── routers/
│   └── review.py          ← /api/reviews/*
└── services/
    └── review_service.py
```

Add to `app/main.py`:
```python
from app.routers import review
app.include_router(review.router, prefix="/api/reviews", tags=["Reviews"])
```

---

## 3. DATABASE MODELS

**Table: `reviews`** — reviews on employer/restaurant
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| employer_id | UUID FK → employer_profiles.id | cascade delete |
| author_id | UUID FK → users.id | cascade delete |
| rating | SMALLINT | CHECK 1–5, not null |
| comment | TEXT | nullable |
| is_visible | BOOLEAN | default True |
| is_flagged | BOOLEAN | default False |
| created_at | TIMESTAMP TZ | default now() |
| UNIQUE | (employer_id, author_id) | one review per user per restaurant |

**Table: `seeker_reviews`** — employers rating seekers
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| seeker_id | UUID FK → seeker_profiles.id | cascade delete |
| employer_id | UUID FK → employer_profiles.id | cascade delete |
| rating | SMALLINT | CHECK 1–5, not null |
| comment | TEXT | nullable |
| created_at | TIMESTAMP TZ | default now() |
| UNIQUE | (seeker_id, employer_id) | one rating per employer per seeker |

**Table: `reports`**
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| reporter_id | UUID FK → users.id | cascade delete |
| target_type | ENUM('vacancy','employer','seeker','review') | not null |
| target_id | UUID | not null — ID of reported content |
| reason | VARCHAR(200) | not null |
| description | TEXT | nullable |
| status | ENUM('pending','reviewed','dismissed') | default 'pending' |
| created_at | TIMESTAMP TZ | default now() |

---

## 4. ALEMBIC MIGRATION

Create: `alembic/versions/006_reviews_reports.py`

Creates ENUM types + all 3 tables.

---

## 5. SCHEMAS

- `ReviewCreate` — rating (1–5) + optional comment
- `ReviewResponse` — full: id, rating, comment, author (name, avatar), created_at, is_flagged
- `SeekerReviewCreate` — rating + optional comment
- `SeekerReviewResponse`
- `ReportCreate` — target_type, target_id, reason, optional description
- `ReportResponse`

---

## 6. ENDPOINTS

### `/api/reviews`

---

**`GET /api/reviews/employer/{employer_id}`** — Get restaurant reviews
- Auth: none — public
- Only return `is_visible = True` reviews
- Order: newest first
- Returns: `PaginatedResponse[ReviewResponse]`
- Include average rating and total count in response (add to meta or separate fields)

---

**`POST /api/reviews/employer/{employer_id}`** — Leave a review
- Auth: any logged-in user (seeker, user, or even employer can review others)
- Cannot review own restaurant → `CANNOT_REVIEW_OWN` (400)
- Duplicate check → `ALREADY_REVIEWED` (409)
- On success: recalculate and update `employer_profiles.rating` and `total_reviews`
- Rating calculation: `AVG(rating)` from all visible reviews, rounded to 1 decimal
- Returns: `ReviewResponse`

---

**`DELETE /api/reviews/{review_id}`** — Delete review
- Auth: `admin` only (users cannot delete their own reviews — contact admin)
- Sets `is_visible = False` (soft delete) rather than hard delete
- Recalculate employer rating after soft delete
- Returns: `SuccessResponse`

---

**`POST /api/reviews/seeker/{seeker_id}`** — Rate a seeker
- Auth: `employer` only
- Employer must have at least one application with status `hired` from this seeker → `NOT_ELIGIBLE_TO_RATE` (403)
- Duplicate → `ALREADY_REVIEWED` (409)
- On success: recalculate `seeker_profiles.rating` and `total_reviews`
- Returns: `SeekerReviewResponse`

---

**`GET /api/reviews/seeker/{seeker_id}`** — Get seeker reviews
- Auth: `employer` or `admin`
- Returns: `PaginatedResponse[SeekerReviewResponse]`

---

**`POST /api/reviews/{review_id}/report`** — Report a review
- Auth: any logged-in user
- Cannot report own review → `CANNOT_REPORT_OWN` (400)
- Sets `reviews.is_flagged = True`
- Creates a `Report` record with target_type = 'review'
- Returns: `SuccessResponse`

---

**`POST /api/reports`** — Report any content
- Auth: any logged-in user
- Body: `ReportCreate` (target_type, target_id, reason, description)
- Validate target exists based on target_type — return `TARGET_NOT_FOUND` (404) if not
- Duplicate report from same user on same target → `ALREADY_REPORTED` (409)
- Returns: `SuccessResponse`

---

### Also implement now (placeholders from earlier sprints):

**`GET /api/employer/reviews`** — Employer sees own restaurant reviews
- Reuse `GET /api/reviews/employer/{employer_id}` logic
- Auth: `employer` required
- Returns: `PaginatedResponse[ReviewResponse]`

---

## 7. ERROR CODES

| Code | Status | When |
|---|---|---|
| `REVIEW_NOT_FOUND` | 404 | |
| `ALREADY_REVIEWED` | 409 | Already left a review |
| `CANNOT_REVIEW_OWN` | 400 | Reviewing own restaurant |
| `NOT_ELIGIBLE_TO_RATE` | 403 | Employer hasn't hired this seeker |
| `CANNOT_REPORT_OWN` | 400 | Reporting own content |
| `ALREADY_REPORTED` | 409 | Already reported this content |
| `TARGET_NOT_FOUND` | 404 | Reported target doesn't exist |

---

## 8. NOTES FOR CURSOR

- Rating recalculation: always compute from scratch using `AVG()` SQL query — don't try to maintain incrementally, it's safer
- `NOT_ELIGIBLE_TO_RATE` check: query applications where `seeker_id = X AND employer_id = current_employer AND status = 'hired'` — if count > 0, allow rating
- Report validation: based on `target_type`, query the correct table to verify target exists
- When a review is flagged 3+ times (from different users), consider auto-hiding it (`is_visible = False`) — implement this if simple, skip if complex

---

*Sprint 6 complete → move to `07_admin.md`*
