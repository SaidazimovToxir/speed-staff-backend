# Sprint 7 — Admin Panel

> Read `00_master.md` first.
> All previous sprints ✅ | Final sprint: Admin Panel

---

## 1. WHAT TO BUILD

Web-based admin panel using FastAPI + Jinja2 HTML templates. No React or separate frontend — server-rendered HTML pages. Accessible at `/admin`.

Also: subscription and payment models (tables only — no payment gateway integration yet).

---

## 2. NEW FILES TO CREATE

```
app/
├── models/
│   └── payment.py         ← Subscription, Payment
├── schemas/
│   └── admin.py
├── routers/
│   └── admin.py           ← /admin/* (HTML) + /api/admin/* (JSON stats)
├── services/
│   └── admin_service.py
└── admin/
    ├── templates/
    │   ├── base.html
    │   ├── login.html
    │   ├── dashboard.html
    │   ├── users.html
    │   ├── user_detail.html
    │   ├── vacancies.html
    │   ├── reviews.html
    │   ├── reports.html
    │   └── documents.html
    └── static/
        └── admin.css
```

Add to `app/main.py`:
```python
from app.routers import admin
app.include_router(admin.router, tags=["Admin"])

from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
app.mount("/admin/static", StaticFiles(directory="app/admin/static"), name="admin_static")
```

---

## 3. DATABASE MODELS (tables only, no payment gateway)

**Table: `subscriptions`**
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users.id | |
| plan | ENUM('monthly','yearly') | |
| plan_type | ENUM('employer_basic','employer_pro') | |
| price | INTEGER | amount in UZS tiyin |
| status | ENUM('active','expired','cancelled') | default 'active' |
| started_at | TIMESTAMP TZ | |
| expires_at | TIMESTAMP TZ | |
| created_at | TIMESTAMP TZ | default now() |

**Table: `payments`**
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users.id | |
| amount | INTEGER | in tiyin |
| currency | VARCHAR(3) | default 'UZS' |
| purpose | ENUM('subscription','premium_vacancy') | |
| payment_method | ENUM('click','payme','card') | |
| status | ENUM('pending','success','failed') | default 'pending' |
| transaction_id | VARCHAR(255) | nullable — gateway ID |
| created_at | TIMESTAMP TZ | default now() |

---

## 4. ALEMBIC MIGRATION

Create: `alembic/versions/007_admin_payments.py`

Creates subscriptions and payments tables.

---

## 5. ADMIN AUTHENTICATION

Simple session-based auth for admin panel (NOT JWT — separate system):

- Admin login credentials from `.env`: `ADMIN_USERNAME` and `ADMIN_PASSWORD`
- On login: set a signed cookie `admin_session` using `itsdangerous` library
- All `/admin/*` HTML routes check this cookie — redirect to `/admin/login` if missing
- Session expires after 8 hours
- This is completely separate from the JWT auth used by the mobile API

Add to `.env`:
```
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_this_in_production
ADMIN_SESSION_SECRET=another-secret-key-for-admin
```

---

## 6. ADMIN HTML PAGES

All pages share `base.html` layout with:
- Left sidebar: navigation links
- Top bar: "Speed Staff Admin" + logged-in username + logout button
- Main content area
- Simple, clean styling — use Tailwind CSS via CDN (no build step)

---

### `GET /admin/login` — Login page
- Form: username + password inputs + "Sign In" button
- `POST /admin/login` — process login, set cookie, redirect to dashboard

---

### `GET /admin` — Dashboard
Show stat cards:
- Total users (by role breakdown)
- Active vacancies
- Applications today
- Pending reports
- Flagged reviews

Recent activity table: last 10 registrations.

---

### `GET /admin/users` — Users list
- Table: id (short), phone, email, role, is_verified, is_blocked, created_at, Actions
- Actions: View | Block/Unblock
- Filters at top: role dropdown, is_blocked toggle, search by phone/email
- Pagination

### `GET /admin/users/{user_id}` — User detail
- Full user info
- Their profile (seeker or employer based on role)
- Block/Unblock button
- Activity summary (applications count, vacancies count)

### `POST /admin/users/{user_id}/block` — Block user
### `POST /admin/users/{user_id}/unblock` — Unblock user
- Form POST (not JSON) — redirect back after action

---

### `GET /admin/vacancies` — Vacancies list
- Table: title, employer, status, is_premium, applications_count, created_at, Actions
- Actions: View (links to public vacancy) | Delete | Toggle Premium
- Filters: status, is_premium

### `POST /admin/vacancies/{id}/delete` — Delete vacancy
### `POST /admin/vacancies/{id}/toggle-premium` — Toggle premium status

---

### `GET /admin/reviews` — Reviews list
- Table: restaurant, author, rating (stars), comment (truncated), is_visible, is_flagged, created_at, Actions
- Actions: Show/Hide | Delete
- Filters: is_flagged (show flagged first by default), is_visible

### `POST /admin/reviews/{id}/hide`
### `POST /admin/reviews/{id}/show`
### `POST /admin/reviews/{id}/delete`

---

### `GET /admin/reports` — Reports list
- Table: reporter, target_type, reason, status, created_at, Actions
- Actions: View Target | Mark Reviewed | Dismiss
- Filters: status (pending first by default), target_type

### `POST /admin/reports/{id}/reviewed`
### `POST /admin/reports/{id}/dismissed`

---

### `GET /admin/documents` — Unverified documents
- Table: seeker name, doc_type, title, uploaded_at, Actions
- Actions: View File | Verify | Delete
- Only shows `is_verified = False` documents by default

### `POST /admin/documents/{id}/verify`
### `POST /admin/documents/{id}/delete`

---

### `POST /admin/employers/{id}/verify` — Give verified badge
- Toggle `employer_profiles.is_verified`
- Can access from Users detail page

---

## 7. JSON API ENDPOINTS (for mobile admin features — future use)

Also add these JSON endpoints (not HTML):

**`GET /api/admin/stats`** — Platform statistics
- Auth: JWT `admin` role required
- Returns:
```json
{
  "users": { "total": 0, "seekers": 0, "employers": 0, "users": 0 },
  "vacancies": { "active": 0, "paused": 0, "closed": 0 },
  "applications": { "total": 0, "today": 0 },
  "reports": { "pending": 0 },
  "reviews": { "flagged": 0 }
}
```

---

## 8. NOTES FOR CURSOR

- Use Jinja2 templates with `Jinja2Templates(directory="app/admin/templates")`
- Use Tailwind CSS via CDN in `base.html`: `<script src="https://cdn.tailwindcss.com"></script>`
- All form actions use standard HTML forms with `POST` method — no JavaScript needed for basic CRUD
- Flash messages: use cookie-based flash messages to show success/error after redirect (e.g. "User blocked successfully")
- Pagination: implement simple page-based pagination with prev/next links in templates
- For "View File" on documents: open `/uploads/documents/{filename}` in new tab
- Keep admin panel simple and functional — not beautiful, just usable
- Add `itsdangerous` to `requirements.txt` for session signing

---

## 9. FINAL CHECKLIST (entire project)

After Sprint 7, verify the complete project:

- [ ] `alembic upgrade head` runs all 7 migrations cleanly
- [ ] All endpoints appear correctly in Swagger at `/docs` with proper tags
- [ ] Auth endpoints still work (didn't break anything)
- [ ] File uploads work and files are served at `/uploads/...`
- [ ] Admin panel accessible at `/admin` with login
- [ ] No blocking DB calls (all async)
- [ ] `requirements.txt` is up to date with all libraries used
- [ ] `.env.example` has all required variables

---

*All sprints complete. 🎉*
*Speed Staff Backend v1.0 — Ready for testing*
