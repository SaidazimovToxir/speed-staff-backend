# Speed Staff — Full Auth Module Implementation Prompt

> Copy this entire prompt and send it to your AI coding assistant (Cursor, Windsurf, Claude, etc.)
> The AI should be able to implement the complete auth module without asking follow-up questions.

---

## PROMPT START

You are an expert Python/FastAPI backend developer. I need you to implement a **complete, production-ready Authentication module** for a mobile app called **Speed Staff** — a platform that connects restaurant workers (waiters, bartenders, cooks) with employers in Uzbekistan.

Do not ask clarifying questions. Implement everything described below exactly as specified.

---

## 1. PROJECT OVERVIEW

**App name:** Speed Staff  
**Backend:** FastAPI (async, Python 3.11+)  
**Database:** PostgreSQL (async via asyncpg + SQLAlchemy 2.0)  
**Auth:** JWT (access + refresh tokens) + SMS OTP  
**API Docs:** Swagger UI (FastAPI built-in at `/docs`)  
**File Storage:** Local filesystem (for now)  
**Target market:** Uzbekistan — SMS via Eskiz.uz

---

## 2. PROJECT STRUCTURE TO CREATE

Create the following file and folder structure. Do not deviate from it:

```
speed_staff/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── common.py
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   └── auth.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   └── otp_service.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── jwt.py
│       ├── hashing.py
│       └── responses.py
│
├── .env
├── .env.example
├── requirements.txt
├── alembic.ini
└── alembic/
    ├── env.py
    └── versions/
        └── 001_create_users_and_otp.py
```

---

## 3. ENVIRONMENT VARIABLES

### `.env.example` (create this file, user will copy and fill in `.env`)

```env
# Application
APP_NAME=Speed Staff
APP_VERSION=1.0.0
DEBUG=True
SECRET_KEY=your-very-secret-key-change-in-production

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/speed_staff

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# OTP
OTP_EXPIRE_MINUTES=5
OTP_LENGTH=6

# Eskiz.uz SMS Gateway
ESKIZ_EMAIL=your@email.com
ESKIZ_PASSWORD=your_eskiz_password
ESKIZ_SENDER=4546

# Google OAuth (optional, can leave empty for now)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# File Upload
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=10

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

---

## 4. DATABASE MODELS

### `app/models/user.py`

Create two SQLAlchemy ORM models:

**Model 1: `User`** — table name `users`

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PRIMARY KEY, default uuid4 |
| phone | VARCHAR(20) | UNIQUE, NOT NULL |
| email | VARCHAR(255) | UNIQUE, NULLABLE |
| password_hash | VARCHAR(255) | NULLABLE |
| role | ENUM('seeker','employer','user','admin') | NOT NULL, default 'user' |
| is_active | BOOLEAN | default True |
| is_verified | BOOLEAN | default False |
| is_blocked | BOOLEAN | default False |
| google_id | VARCHAR(255) | UNIQUE, NULLABLE |
| apple_id | VARCHAR(255) | UNIQUE, NULLABLE |
| created_at | TIMESTAMP WITH TIMEZONE | default now() |
| updated_at | TIMESTAMP WITH TIMEZONE | default now(), onupdate now() |

**Model 2: `OTPCode`** — table name `otp_codes`

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PRIMARY KEY, default uuid4 |
| phone | VARCHAR(20) | NOT NULL, INDEX |
| code | VARCHAR(6) | NOT NULL |
| purpose | ENUM('register','login','reset','verify') | NOT NULL |
| is_used | BOOLEAN | default False |
| attempts | SMALLINT | default 0 |
| expires_at | TIMESTAMP WITH TIMEZONE | NOT NULL |
| created_at | TIMESTAMP WITH TIMEZONE | default now() |

---

## 5. PYDANTIC SCHEMAS

### `app/schemas/common.py`

Create these reusable schemas used across the entire project:

```python
# These are the EXACT schemas to implement:

class Meta(BaseModel):
    """Pagination metadata"""
    page: int
    limit: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list response"""
    items: List[T]
    meta: Meta

class SuccessResponse(BaseModel):
    """Simple success message"""
    success: bool = True
    message: str

class ErrorDetail(BaseModel):
    """Standard error response"""
    success: bool = False
    error_code: str        # machine-readable e.g. "INVALID_OTP", "USER_NOT_FOUND"
    message: str           # human-readable
    details: Optional[Any] = None  # optional extra info (validation errors etc.)
```

**IMPORTANT:** All API responses — success or error — must follow these schemas.
Never return raw strings or unstructured dicts.

### `app/schemas/auth.py`

```python
# Request schemas:

class SendOTPRequest:
    phone: str  # must be E.164 format, e.g. +998901234567
    purpose: Literal['register', 'login', 'reset']

class VerifyOTPRequest:
    phone: str
    code: str
    purpose: Literal['register', 'login', 'reset']

class RegisterWithEmailRequest:
    email: EmailStr
    password: str  # min 8 chars, at least 1 digit
    role: Literal['seeker', 'employer', 'user']
    phone: str  # still required even for email register

class LoginWithEmailRequest:
    email: EmailStr
    password: str

class RefreshTokenRequest:
    refresh_token: str

class ChangePasswordRequest:
    old_password: str
    new_password: str  # min 8 chars

class GoogleAuthRequest:
    id_token: str  # Google ID token from mobile client


# Response schemas:

class TokenResponse:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # access token TTL in seconds

class UserResponse:
    id: UUID
    phone: str
    email: Optional[str]
    role: str
    is_verified: bool
    is_blocked: bool
    created_at: datetime

class AuthResponse:
    user: UserResponse
    tokens: TokenResponse
```

---

## 6. AUTH ENDPOINTS

### Router: `app/routers/auth.py`
### Prefix: `/api/auth`
### Swagger tag: `"Auth"`

Implement ALL of the following endpoints:

---

#### `POST /api/auth/send-otp`
**Purpose:** Send a 6-digit OTP SMS to a phone number.

**Request body:** `SendOTPRequest`

**Logic:**
1. Validate phone format (must start with +998 and be 13 chars total)
2. Check if there's an unexpired, unused OTP for this phone+purpose — if yes, return error `OTP_ALREADY_SENT` with remaining seconds
3. Generate a random 6-digit code
4. Save to `otp_codes` table with expiry = now + OTP_EXPIRE_MINUTES
5. Send SMS via Eskiz.uz (see Section 8)
6. In DEBUG mode: also return the code in the response (for testing without real SMS)
7. Return: `SuccessResponse` with message "OTP sent successfully"

**Errors:**
- `INVALID_PHONE_FORMAT` (400) — wrong phone format
- `OTP_ALREADY_SENT` (429) — OTP already sent, include `retry_after` seconds in details
- `SMS_SEND_FAILED` (503) — Eskiz failed to send

---

#### `POST /api/auth/verify-otp`
**Purpose:** Verify OTP and log in or register the user.

**Request body:** `VerifyOTPRequest`

**Logic:**
1. Find the latest unexpired, unused OTP for phone+purpose
2. If not found → `OTP_NOT_FOUND` (404)
3. If expired → `OTP_EXPIRED` (400)
4. Increment `attempts`. If attempts >= 5 → mark as used, return `OTP_MAX_ATTEMPTS` (400)
5. If code doesn't match → `OTP_INVALID` (400)
6. Mark OTP as used (`is_used = True`)
7. If purpose == `register`:
   - If user with this phone already exists → `USER_ALREADY_EXISTS` (409)
   - Create new user with `is_verified = True`, role defaults to `'user'`
   - Return `AuthResponse` with tokens
8. If purpose == `login`:
   - If user not found → `USER_NOT_FOUND` (404)
   - If user is blocked → `USER_BLOCKED` (403)
   - Return `AuthResponse` with tokens
9. If purpose == `reset`:
   - Just return `SuccessResponse` — password reset flow handled separately

---

#### `POST /api/auth/register/email`
**Purpose:** Register with email + password.

**Request body:** `RegisterWithEmailRequest`

**Logic:**
1. Validate password strength (min 8 chars, at least 1 digit)
2. Check if email already exists → `EMAIL_ALREADY_EXISTS` (409)
3. Check if phone already exists → `PHONE_ALREADY_EXISTS` (409)
4. Hash password with bcrypt
5. Create user with `is_verified = False`
6. Return `AuthResponse` with tokens

---

#### `POST /api/auth/login/email`
**Purpose:** Login with email + password.

**Request body:** `LoginWithEmailRequest`

**Logic:**
1. Find user by email → `USER_NOT_FOUND` (404) if not found
2. If user is blocked → `USER_BLOCKED` (403)
3. If password_hash is None → `OAUTH_ACCOUNT` (400) — user registered via Google, no password
4. Verify password → `INVALID_CREDENTIALS` (401) if wrong
5. Return `AuthResponse` with tokens

---

#### `POST /api/auth/google`
**Purpose:** Google OAuth login/register.

**Request body:** `GoogleAuthRequest`

**Logic:**
1. Verify the Google ID token using Google's public keys (use `google-auth` library)
2. Extract: `google_id`, `email`, `name` from token payload
3. Try to find user by `google_id` → if found, login
4. Try to find user by `email` → if found, link `google_id` and login
5. If not found → create new user with `is_verified = True`
6. If user is blocked → `USER_BLOCKED` (403)
7. Return `AuthResponse` with tokens

---

#### `POST /api/auth/refresh`
**Purpose:** Get a new access token using refresh token.

**Request body:** `RefreshTokenRequest`

**Logic:**
1. Decode and validate refresh token
2. Check token type is "refresh" → `INVALID_TOKEN_TYPE` (400)
3. Find user by ID from token → `USER_NOT_FOUND` (404)
4. If user is blocked → `USER_BLOCKED` (403)
5. Issue new access token (keep same refresh token)
6. Return `TokenResponse`

---

#### `POST /api/auth/logout`
**Purpose:** Logout (client-side, server just confirms).

**Auth required:** Yes (Bearer token in header)

**Logic:**
1. Validate access token
2. Return `SuccessResponse` with message "Logged out successfully"
3. Note: Token blacklisting is NOT required for now — client simply discards tokens

---

#### `POST /api/auth/change-password`
**Purpose:** Change password for authenticated user.

**Auth required:** Yes (Bearer token in header)

**Request body:** `ChangePasswordRequest`

**Logic:**
1. Get current user from token
2. If user has no password (OAuth user) → `OAUTH_ACCOUNT` (400)
3. Verify old password → `INVALID_CREDENTIALS` (401)
4. Validate new password strength
5. Hash and save new password
6. Return `SuccessResponse`

---

## 7. JWT UTILITY

### `app/utils/jwt.py`

Implement the following functions:

```python
def create_access_token(user_id: str, role: str) -> str:
    """
    Payload: { sub: user_id, role: role, type: "access", exp: ... }
    Signed with SECRET_KEY using HS256
    """

def create_refresh_token(user_id: str) -> str:
    """
    Payload: { sub: user_id, type: "refresh", exp: ... }
    """

def decode_token(token: str) -> dict:
    """
    Decode and validate. Raise HTTPException 401 if invalid or expired.
    """

def create_token_pair(user_id: str, role: str) -> TokenResponse:
    """
    Create both tokens and return TokenResponse schema.
    """
```

---

## 8. SMS SERVICE (ESKIZ.UZ)

### `app/services/otp_service.py`

Eskiz.uz API flow:
1. First, get auth token: `POST https://notify.eskiz.uz/api/auth/login` with `{email, password}`
2. Token expires — refresh it: `PATCH https://notify.eskiz.uz/api/auth/refresh`
3. Send SMS: `POST https://notify.eskiz.uz/api/message/sms/send` with:
   ```json
   {
     "mobile_phone": "998901234567",  // without + sign
     "message": "Speed Staff: Your code is 123456. Valid for 5 minutes.",
     "from": "4546",
     "callback_url": ""
   }
   ```
4. Use `httpx.AsyncClient` for all HTTP requests (async)
5. Cache the Eskiz token in memory (module-level variable) — re-authenticate if token is expired (401 response)
6. In DEBUG mode: skip actual SMS sending, just log the code to console

Implement a class `EskizSMSService` with:
```python
class EskizSMSService:
    async def send_otp(self, phone: str, code: str) -> bool: ...
    async def _get_token(self) -> str: ...
    async def _refresh_token(self) -> str: ...
```

---

## 9. DEPENDENCIES

### `app/dependencies.py`

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Decode JWT, get user from DB.
    Raise 401 if token invalid.
    Raise 403 if user is blocked.
    """

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Same as above but also checks is_active."""

def require_role(*roles: str):
    """
    Factory that returns a dependency checking user role.
    Usage: Depends(require_role("admin", "employer"))
    """
```

---

## 10. MAIN APP SETUP

### `app/main.py`

```python
# Configure FastAPI with:
app = FastAPI(
    title="Speed Staff API",
    description="Backend API for Speed Staff — restaurant staffing platform",
    version="1.0.0",
    docs_url="/docs",         # Swagger UI
    redoc_url="/redoc",       # ReDoc
    openapi_url="/openapi.json"
)

# Add CORS middleware — allow all origins for now (restrict in production)
# Add the auth router with prefix /api/auth and tag "Auth"
# Add a root endpoint GET / that returns app info
# Add global exception handler for unhandled exceptions → return ErrorDetail schema
# Add handler for RequestValidationError → return ErrorDetail with error_code "VALIDATION_ERROR"
```

### Swagger security scheme:
Configure Swagger to show the "Authorize" button so testers can paste Bearer tokens:
```python
from fastapi.security import HTTPBearer
security = HTTPBearer()
```
Add `security=[{"BearerAuth": []}]` to protected endpoints.

---

## 11. DATABASE SETUP

### `app/database.py`

```python
# Use SQLAlchemy 2.0 async engine
# async_sessionmaker for session factory
# Base = DeclarativeBase()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### `app/config.py`

Use `pydantic-settings` `BaseSettings` class. Read all variables from `.env` file automatically.

---

## 12. ALEMBIC MIGRATION

### `alembic/versions/001_create_users_and_otp.py`

Write the migration that creates:
1. The `userrole` ENUM type: `('seeker', 'employer', 'user', 'admin')`
2. The `otppurpose` ENUM type: `('register', 'login', 'reset', 'verify')`
3. The `users` table with all columns
4. The `otp_codes` table with all columns
5. Indexes: `ix_otp_codes_phone` on `otp_codes.phone`

---

## 13. ERROR CODES REFERENCE

All error codes the auth module can return. Use these EXACT strings:

| Error Code | HTTP Status | When |
|---|---|---|
| `INVALID_PHONE_FORMAT` | 400 | Phone not in +998XXXXXXXXX format |
| `OTP_ALREADY_SENT` | 429 | Unexpired OTP exists |
| `OTP_NOT_FOUND` | 404 | No OTP found for phone+purpose |
| `OTP_EXPIRED` | 400 | OTP exists but expired |
| `OTP_INVALID` | 400 | Wrong code |
| `OTP_MAX_ATTEMPTS` | 400 | 5 wrong attempts |
| `SMS_SEND_FAILED` | 503 | Eskiz API failed |
| `USER_NOT_FOUND` | 404 | No user with this phone/email |
| `USER_ALREADY_EXISTS` | 409 | Phone already registered |
| `EMAIL_ALREADY_EXISTS` | 409 | Email already registered |
| `PHONE_ALREADY_EXISTS` | 409 | Phone already registered (email flow) |
| `USER_BLOCKED` | 403 | Admin blocked this user |
| `INVALID_CREDENTIALS` | 401 | Wrong password |
| `OAUTH_ACCOUNT` | 400 | User has no password (Google account) |
| `INVALID_TOKEN` | 401 | JWT invalid or expired |
| `INVALID_TOKEN_TYPE` | 400 | Wrong token type (access vs refresh) |
| `VALIDATION_ERROR` | 422 | Pydantic validation failed |
| `WEAK_PASSWORD` | 400 | Password doesn't meet requirements |
| `GOOGLE_TOKEN_INVALID` | 400 | Google ID token verification failed |

---

## 14. REQUIREMENTS.TXT

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
alembic==1.14.0
pydantic==2.10.0
pydantic-settings==2.7.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.19
httpx==0.28.0
google-auth==2.37.0
aiofiles==24.1.0
```

---

## 15. FINAL CHECKLIST

After implementing, make sure:

- [ ] `GET /docs` shows Swagger UI with all 8 auth endpoints grouped under "Auth" tag
- [ ] Every endpoint has a proper summary, description, and response schema in Swagger
- [ ] Every response (success and error) uses `SuccessResponse`, `AuthResponse`, `TokenResponse`, or `ErrorDetail`
- [ ] `PaginatedResponse[T]` and `Meta` are in `common.py` ready to use in future modules
- [ ] OTP code is logged to console in DEBUG=True mode (so dev can test without real SMS)
- [ ] All DB operations use `async/await` — no blocking calls
- [ ] Alembic migration runs cleanly with `alembic upgrade head`
- [ ] `.env.example` is present, `.env` is in `.gitignore`
- [ ] Phone validation accepts only Uzbek numbers: `+998XXXXXXXXX` (13 chars)
- [ ] `require_role()` dependency is ready even though it's not used in auth yet

---

## HOW TO RUN (add this as a comment in `main.py`)

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and fill environment variables
cp .env.example .env

# 4. Run database migrations
alembic upgrade head

# 5. Start the server
uvicorn app.main:app --reload --port 8000

# 6. Open Swagger UI
# http://localhost:8000/docs
```

---

## PROMPT END
