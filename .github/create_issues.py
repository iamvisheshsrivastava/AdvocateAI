"""
Script to create GitHub issues for identified bugs and improvements in AdvocateAI.
Run via: python .github/create_issues.py
Requires GITHUB_TOKEN and GITHUB_REPOSITORY environment variables.
"""

import json
import os
import sys
import urllib.request
import urllib.error

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")


def create_issue(title, body, labels=None):
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/issues"
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            print(f"Created issue #{result['number']}: {title}")
            return result["number"]
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(f"ERROR creating '{title}': HTTP {e.code} - {body_text}", file=sys.stderr)
        return None


ISSUES = [
    {
        "title": "[Security] Passwords stored and compared in plain text",
        "labels": ["bug", "security"],
        "body": """## Description

The application stores user passwords in plain text in the database and compares them directly in SQL queries. This is a critical security vulnerability.

## Location

- `backend/routers/auth.py` – The login query uses `COALESCE(password_hash, password) = %s OR password = %s`, comparing plain-text passwords.
- `backend/db/database.py` – The migration sets `password_hash = COALESCE(password_hash, password)`, storing the same plain-text value in both columns.
- `backend/routers/auth.py` (signup) – Password is stored as-is in both `password` and `password_hash` columns.

## Impact

If the database is compromised, all user passwords are immediately exposed. Attackers can use these passwords in credential-stuffing attacks across other services since users often reuse passwords.

## Recommendation

Use a strong, slow hashing algorithm such as **bcrypt** or **argon2** (via the `passlib` library) to hash passwords before storing them.

```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

hashed = pwd_context.hash(plain_password)           # on signup
is_valid = pwd_context.verify(plain_password, hashed)  # on login
```

Remove the plain-text `password` column from the `users` table and only keep `password_hash`.

## Severity

Critical""",
    },
    {
        "title": "[Security] No server-side session or token authentication",
        "labels": ["bug", "security"],
        "body": """## Description

API endpoints accept a `user_id` in the request body or query parameters to identify the acting user, but there is no server-side verification that the caller actually owns that identity. Any client can impersonate any user by simply sending a different `user_id`.

## Location

- `backend/routers/cases.py` – `POST /cases/create` uses `data.client_id` from the request body without verifying a session token.
- `backend/routers/messages.py` – `POST /messages/send` uses `data.sender_id` without authentication.
- `backend/routers/lawyers.py` – `POST /lawyer/profile` uses `data.lawyer_id` without authentication.
- All other write endpoints follow the same pattern.

## Impact

Any unauthenticated user can create cases, send messages, apply to cases, or modify profiles on behalf of any other user by guessing or knowing their `user_id`.

## Recommendation

Implement JWT-based authentication:
1. On login, generate a signed JWT containing `user_id` and `role` with an expiry.
2. Return the token to the client.
3. Add a FastAPI dependency (`Depends(get_current_user)`) that validates the JWT on every protected endpoint.
4. Compare the token's `user_id` with any resource-owner IDs in the request.

```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    return payload  # contains user_id, role
```

## Severity

Critical""",
    },
    {
        "title": "[Security] Wildcard CORS policy allows any origin",
        "labels": ["bug", "security"],
        "body": """## Description

The FastAPI application uses `allow_origins=["*"]`, which permits requests from any domain. When combined with `allow_credentials=True`, this violates the CORS specification and exposes the API to cross-site request forgery (CSRF) attacks.

## Location

`backend/app.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,   # invalid with wildcard origin
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Impact

Malicious websites can make credentialed requests to the API on behalf of logged-in users. Browsers actually reject `allow_credentials=True` with a wildcard origin per the CORS spec, which may also cause CORS failures for legitimate clients.

## Recommendation

Restrict `allow_origins` to an explicit list of trusted frontend domains:
```python
allow_origins=[
    "https://advocateai.example.com",
    "http://localhost:8080",  # development only
],
allow_credentials=True,
```

## Severity

High""",
    },
    {
        "title": "[Bug] Database connections leak when exceptions are raised",
        "labels": ["bug"],
        "body": """## Description

Throughout the backend routers and services, database connections are obtained with `get_db_connection()` and closed manually at the end of each function. If any exception is raised between acquiring the connection and the close calls, the connection is never returned, causing a connection leak. Over time this will exhaust the PostgreSQL connection limit.

## Location

Examples across multiple files:
- `backend/routers/auth.py` – `login()`, `signup()`
- `backend/routers/cases.py` – `create_case()`, `apply_to_case()`, `get_recommended_cases_for_lawyer()`
- `backend/routers/lawyers.py` – `upsert_lawyer_profile()`, `get_watchlist()`
- `backend/services/matching_service.py` – `refresh_lawyer_responsiveness()`

## Recommendation

Wrap all database operations in a `try/finally` block to guarantee the connection is always closed:

```python
conn = get_db_connection()
try:
    cur = conn.cursor()
    cur.execute(...)
    conn.commit()
finally:
    cur.close()
    conn.close()
```

Alternatively, implement `get_db_connection()` as a context manager, or use a connection pool that automatically recycles connections.

## Severity

High""",
    },
    {
        "title": "[Bug] Missing HTTP 404 responses — endpoints return empty objects on missing resources",
        "labels": ["bug"],
        "body": """## Description

Several GET endpoints silently return an empty object (`{}`) or empty array (`[]`) when a requested resource does not exist, instead of returning a proper HTTP 404 response. This makes it impossible for clients to distinguish "resource not found" from "resource exists but is empty".

## Location

- `backend/routers/cases.py` – `get_case_detail()` returns `{}` when the case is not found.
- `backend/routers/lawyers.py` – `get_lawyer_profile()` returns `{}` when the profile is not found.
- `backend/routers/cases.py` – `get_case_events()` does not raise 404 if the case does not exist.

## Example Fix

```python
from fastapi import HTTPException

# Before (incorrect)
if not row:
    return {}

# After (correct)
if not row:
    raise HTTPException(status_code=404, detail="Case not found.")
```

## Impact

The Flutter frontend cannot reliably detect missing resources, leading to silent UI failures and confusing user experiences (blank screens instead of error messages).

## Severity

Medium""",
    },
    {
        "title": "[Bug] No pagination on GET /cases/open — returns all cases at once",
        "labels": ["bug", "performance"],
        "body": """## Description

The `GET /cases/open` endpoint fetches every open public case from the database in a single query with no `LIMIT` or cursor-based pagination. As the number of cases grows, this will cause slow queries, high memory usage, and large response payloads.

## Location

`backend/routers/cases.py` – `get_open_cases()`:
```python
cur.execute(
    \"\"\"
    SELECT ... FROM cases c
    WHERE c.status = 'open' AND c.is_public = TRUE
    ORDER BY c.created_at DESC
    \"\"\"
)
rows = cur.fetchall()
```

The same issue exists in `GET /cases/recommended/{lawyer_id}` and `GET /professionals/{user_id}`.

## Recommendation

Add `limit` and `offset` query parameters:
```python
@router.get("/cases/open")
async def get_open_cases(limit: int = 20, offset: int = 0):
    ...
    cur.execute(
        "SELECT ... LIMIT %s OFFSET %s",
        (min(limit, 100), max(offset, 0))
    )
```

## Severity

Medium""",
    },
    {
        "title": "[Bug] Placeholder email generated on signup — users cannot provide a real email",
        "labels": ["bug"],
        "body": """## Description

The signup endpoint auto-generates a fake email address (`{username}@advocateai.local`) instead of accepting the user's real email. This prevents email-based features such as password reset, notifications, or account verification from ever working.

## Location

`backend/routers/auth.py`:
```python
email = f"{username}@advocateai.local"
```

`backend/models/user.py` – The `SignupRequest` model has no `email` field:
```python
class SignupRequest(BaseModel):
    username: str
    password: str
    role: str = "client"
```

## Recommendation

1. Add an `email` field to `SignupRequest` using Pydantic's `EmailStr` for format validation.
2. Check for email uniqueness during signup.
3. Store the user-provided email rather than a placeholder.

```python
from pydantic import EmailStr

class SignupRequest(BaseModel):
    username: str
    password: str
    email: EmailStr
    role: str = "client"
```

## Severity

Medium""",
    },
    {
        "title": "[Performance] No database connection pooling — new TCP connection per request",
        "labels": ["performance"],
        "body": """## Description

Every API request calls `get_db_connection()`, which opens a brand-new TCP connection to PostgreSQL via `psycopg2.connect()`. Establishing a connection is expensive (~10–50 ms overhead) and PostgreSQL has a hard limit on simultaneous connections (default: 100). Under any moderate load this will cause latency spikes and potential connection exhaustion.

## Location

`backend/db/database.py`:
```python
def get_db_connection():
    return psycopg2.connect(
        host=..., database=..., user=..., password=..., port=...
    )  # new TCP connection on every call
```

## Recommendation

Use a connection pool such as `psycopg2.pool.ThreadedConnectionPool`:

```python
from psycopg2 import pool

_pool = pool.ThreadedConnectionPool(
    minconn=2, maxconn=20,
    host=DB_HOST, database=DB_NAME,
    user=DB_USER, password=DB_PASSWORD, port=DB_PORT,
)

def get_db_connection():
    return _pool.getconn()

def release_db_connection(conn):
    _pool.putconn(conn)
```

For a fully async FastAPI application, consider migrating to `asyncpg` with `asyncpg.create_pool()`.

## Severity

High""",
    },
    {
        "title": "[Security] No file size or MIME type validation on document upload endpoint",
        "labels": ["bug", "security"],
        "body": """## Description

The `POST /documents/analyze` endpoint accepts file uploads but does not enforce a maximum file size or validate that uploaded files match their declared content type. This can be exploited to:
- Upload arbitrarily large files, exhausting server memory or disk space.
- Upload malicious files disguised as PDFs or images.

## Location

`backend/routers/documents.py`:
```python
file_bytes = await upload.read()  # no size check before reading entire file
```

## Recommendation

1. Enforce a maximum file size (e.g., 10 MB) before reading the full content:
```python
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
file_bytes = await upload.read(MAX_FILE_SIZE_BYTES + 1)
if len(file_bytes) > MAX_FILE_SIZE_BYTES:
    raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")
```

2. Validate the MIME type against an allowlist:
```python
ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
if upload.content_type not in ALLOWED_TYPES:
    raise HTTPException(status_code=415, detail=f"Unsupported file type: {upload.content_type}")
```

## Severity

High""",
    },
    {
        "title": "[Enhancement] No input length validation on text fields",
        "labels": ["enhancement"],
        "body": """## Description

The Pydantic request models do not define any maximum length constraints on text fields. Users can submit arbitrarily long strings for titles, descriptions, messages, and other fields, which get inserted directly into the database. This can cause:
- Database row size limits to be hit unexpectedly.
- Excessively large payloads being sent to the Gemini AI API, wasting quota.
- Denial-of-service via very large inputs.

## Location

- `backend/models/case.py` – `title`, `description`, `ai_summary` have no length limits.
- `backend/models/message.py` – `content` has no length limit.
- `backend/models/user.py` – `username`, `password` have no length limits.
- `backend/models/lawyer.py` – `bio`, `practice_areas`, `languages` have no length limits.

## Recommendation

Use Pydantic's `Field` with `max_length` constraints:

```python
from pydantic import BaseModel, Field

class CaseCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
```

Add corresponding `VARCHAR(n)` constraints to the PostgreSQL schema as a second layer of defence.

## Severity

Medium""",
    },
    {
        "title": "[Enhancement] Payment processing not implemented — Premium page is non-functional",
        "labels": ["enhancement"],
        "body": """## Description

The application includes a Premium pricing page (`test_app/lib/premium_page.dart`) with subscription tiers, but there is no backend payment processing integration. The upgrade buttons do not trigger any payment flow, making the premium feature completely non-functional.

## Location

- `test_app/lib/premium_page.dart` – UI exists but buttons have no backend action.
- `backend/services/integration_placeholders.py` – Payment integration is listed as a placeholder.

## Recommendation

Integrate a payment provider such as **Stripe**:
1. Add `POST /payments/create-checkout-session` using the Stripe Python SDK.
2. Handle Stripe webhooks (`payment_intent.succeeded`) to update subscription status in the database.
3. Add a `subscription_tier` column to the `users` table.
4. Gate premium features (e.g., unlimited AI queries, priority lawyer matching) behind a subscription check middleware.

## Severity

Medium""",
    },
    {
        "title": "[Testing] No automated backend tests",
        "labels": ["enhancement"],
        "body": """## Description

The backend has zero automated tests. There are no unit tests, integration tests, or API endpoint tests. The only test file in the repository is a default Flutter widget counter test (`test_app/test/widget_test.dart`) that tests a counter widget that doesn't exist in the actual app.

## Impact

- Bugs and regressions are only discovered manually or in production.
- Refactoring is risky with no safety net.
- New contributors have no specification of expected behaviour.
- CI/CD pipeline (`deploy.yml`) deploys without any test gate.

## Recommendation

Add a backend test suite using **pytest** and FastAPI's **TestClient**:

```python
# backend/tests/test_auth.py
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_signup_creates_user():
    res = client.post("/signup", json={
        "username": "testuser", "password": "s3cr3t", "role": "client"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "user_id" in data

def test_login_with_valid_credentials():
    res = client.post("/login", json={"username": "testuser", "password": "s3cr3t"})
    assert res.json()["success"] is True
```

Also add the test run as a required step in `.github/workflows/deploy.yml` before the deploy step.

## Severity

Medium""",
    },
]


def main():
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    if not GITHUB_REPOSITORY:
        print("ERROR: GITHUB_REPOSITORY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Creating {len(ISSUES)} issues in {GITHUB_REPOSITORY}...")
    created = 0
    for issue in ISSUES:
        num = create_issue(issue["title"], issue["body"], issue.get("labels"))
        if num:
            created += 1

    print(f"\nDone: {created}/{len(ISSUES)} issues created.")
    if created < len(ISSUES):
        sys.exit(1)


if __name__ == "__main__":
    main()
