import json
from pathlib import Path
from threading import Lock

from fastapi import APIRouter

from auth_utils import create_access_token
from db.database import get_db_connection
from logging_config import get_logger
from models.user import LoginRequest, SignupRequest
from security import hash_password, is_legacy_password_hash, verify_password

logger = get_logger(__name__)

router = APIRouter(tags=["auth"])
_LOCAL_USERS_FILE = Path(__file__).resolve().parent.parent / "data" / "local_users.json"
_LOCAL_USERS_LOCK = Lock()


def _normalize_role(role: str | None) -> str:
    normalized = (role or "client").strip().lower()
    return normalized if normalized in ("client", "lawyer", "admin") else "client"


def _load_local_users() -> list[dict]:
    if not _LOCAL_USERS_FILE.exists():
        return []
    try:
        with _LOCAL_USERS_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []
    except Exception:
        logger.exception("Failed to load local users file")
        return []


def _save_local_users(users: list[dict]) -> None:
    _LOCAL_USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _LOCAL_USERS_FILE.open("w", encoding="utf-8") as fh:
        json.dump(users, fh, ensure_ascii=True, indent=2)


def _find_local_user_by_login(username: str, password: str) -> dict | None:
    normalized = username.strip().lower()
    users = _load_local_users()
    for user in users:
        if str(user.get("name", "")).strip().lower() != normalized:
            continue
        stored = str(user.get("password_hash") or user.get("password") or "")
        if verify_password(password, stored):
            if is_legacy_password_hash(stored) or user.get("password"):
                user["password_hash"] = hash_password(password)
                user.pop("password", None)
                _save_local_users(users)
            return user
    return None


def _create_local_user(username: str, password: str, email: str, role: str) -> dict:
    with _LOCAL_USERS_LOCK:
        users = _load_local_users()
        if any(str(u.get("name", "")).strip().lower() == username.strip().lower() for u in users):
            raise ValueError("Username already exists.")
        if any(str(u.get("email", "")).strip().lower() == email.strip().lower() for u in users):
            raise ValueError("An account with this email already exists.")
        next_id = max((int(u.get("id", 0)) for u in users), default=0) + 1
        user = {
            "id": next_id,
            "name": username,
            "email": email,
            "password_hash": hash_password(password),
            "role": role,
        }
        users.append(user)
        _save_local_users(users)
        return user


def _token_response(user_id: int, username: str, email: str, role: str) -> dict:
    token = create_access_token(user_id=user_id, role=role, email=email)
    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "username": username,
        "email": email,
        "role": role,
    }


@router.post("/login")
async def login(data: LoginRequest):
    username = data.username.strip()
    password = data.password.strip()

    if not username or not password:
        return {"success": False, "message": "Username and password are required."}

    conn = cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, email, COALESCE(role, 'client'), password_hash, password
            FROM users
            WHERE (LOWER(name) = LOWER(%s) OR LOWER(email) = LOWER(%s))
            LIMIT 1
            """,
            (username, username),
        )
        row = cur.fetchone()
        if row and verify_password(password, row[4] or row[5]):
            if is_legacy_password_hash(row[4]) or row[5]:
                cur.execute(
                    "UPDATE users SET password = NULL, password_hash = %s WHERE id = %s",
                    (hash_password(password), row[0]),
                )
                conn.commit()
            return _token_response(row[0], row[1], row[2], row[3])
    except Exception:
        logger.exception("DB login failed for %s, trying local fallback", username)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    user = _find_local_user_by_login(username, password)
    if user:
        return _token_response(int(user["id"]), user["name"], user["email"], user.get("role", "client"))

    return {"success": False, "message": "Invalid username or password."}


@router.post("/signup")
async def signup(data: SignupRequest):
    username = data.username.strip()
    password = data.password.strip()
    email = data.email.strip().lower()
    role = _normalize_role(data.role)

    if not username or not password:
        return {"success": False, "message": "Username and password are required."}

    conn = cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE LOWER(name) = LOWER(%s)", (username,))
        if cur.fetchone():
            return {"success": False, "message": "Username already exists."}
        cur.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(%s)", (email,))
        if cur.fetchone():
            return {"success": False, "message": "An account with this email already exists."}
        cur.execute(
            "INSERT INTO users (name, email, password, password_hash, role) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (username, email, None, hash_password(password), role),
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        return _token_response(user_id, username, email, role)
    except Exception as exc:
        logger.exception("DB signup failed, falling back to local users")
        try:
            user = _create_local_user(username, password, email, role)
            return _token_response(int(user["id"]), user["name"], user["email"], user.get("role", "client"))
        except ValueError as local_exc:
            return {"success": False, "message": str(local_exc)}
        except Exception:
            logger.exception("Local user creation also failed")
            return {"success": False, "message": f"Unable to create account: {exc}"}
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
