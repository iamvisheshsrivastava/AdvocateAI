import json
from pathlib import Path
from threading import Lock

from fastapi import APIRouter
from db.database import get_db_connection
from logging_config import get_logger

logger = get_logger(__name__)
from models.user import LoginRequest, SignupRequest

router = APIRouter(tags=["auth"])
_LOCAL_USERS_FILE = Path(__file__).resolve().parent.parent / "data" / "local_users.json"
_LOCAL_USERS_LOCK = Lock()


def _normalize_role(role: str | None) -> str:
    normalized = (role or "client").strip().lower()
    if normalized in ("client", "lawyer", "admin"):
        return normalized
    return "client"


def _load_local_users() -> list[dict]:
    if not _LOCAL_USERS_FILE.exists():
        return []

    try:
        with _LOCAL_USERS_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    except Exception as exc:
        logger.exception("Failed to load local users file")

    return []


def _save_local_users(users: list[dict]) -> None:
    _LOCAL_USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _LOCAL_USERS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(users, handle, ensure_ascii=True, indent=2)


def _local_user_payload(user: dict) -> dict:
    return {
        "success": True,
        "user_id": int(user["id"]),
        "username": user["name"],
        "email": user["email"],
        "role": user.get("role", "client"),
    }


def _find_local_user_by_name(username: str) -> dict | None:
    normalized = username.strip().lower()
    for user in _load_local_users():
        if str(user.get("name", "")).strip().lower() == normalized:
            return user
    return None


def _find_local_user_by_login(username: str, password: str) -> dict | None:
    normalized = username.strip().lower()
    for user in _load_local_users():
        if str(user.get("name", "")).strip().lower() != normalized:
            continue
        stored_password = str(user.get("password_hash") or user.get("password") or "")
        if stored_password == password:
            return user
    return None


def _create_local_user(username: str, password: str, role: str) -> dict:
    with _LOCAL_USERS_LOCK:
        users = _load_local_users()
        existing = next(
            (
                user
                for user in users
                if str(user.get("name", "")).strip().lower() == username.strip().lower()
            ),
            None,
        )
        if existing is not None:
            raise ValueError("Username already exists.")

        next_id = max([int(user.get("id", 0)) for user in users], default=0) + 1
        user = {
            "id": next_id,
            "name": username,
            "email": f"{username}@advocateai.local",
            "password": password,
            "password_hash": password,
            "role": role,
        }
        users.append(user)
        _save_local_users(users)
        return user


@router.post("/login")
async def login(data: LoginRequest):
    username = data.username.strip()
    password = data.password.strip()

    if not username or not password:
        return {"success": False}

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, email, COALESCE(role, 'client')
            FROM users
            WHERE (LOWER(name) = LOWER(%s) OR LOWER(email) = LOWER(%s))
              AND (COALESCE(password_hash, password) = %s OR password = %s)
            """,
            (username, username, password, password),
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            return {
                "success": True,
                "user_id": user[0],
                "username": user[1],
                "email": user[2],
                "role": user[3],
            }
    except Exception as exc:
        logger.exception("Database login lookup failed for %s", username)
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()

    local_user = _find_local_user_by_login(username, password)
    if local_user is not None:
        return _local_user_payload(local_user)

    return {"success": False}


@router.post("/signup")
async def signup(data: SignupRequest):
    username = data.username.strip()
    password = data.password.strip()
    role = _normalize_role(data.role)

    if not username or not password:
        return {"success": False, "message": "Username and password are required."}

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE LOWER(name) = LOWER(%s)", (username,))
        existing = cur.fetchone()

        if existing:
            return {"success": False, "message": "Username already exists."}

        email = f"{username}@advocateai.local"
        cur.execute(
            """
            INSERT INTO users (name, email, password, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (username, email, password, password, role),
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        return {"success": True, "user_id": user_id, "username": username, "role": role}
    except Exception as exc:
        logger.exception("Signup failed using DB, falling back to local users: %s", exc)
        try:
            local_user = _create_local_user(username, password, role)
            return _local_user_payload(local_user)
        except ValueError as local_exc:
            return {"success": False, "message": str(local_exc)}
        except Exception:
            logger.exception("Failed to create local fallback user")
            return {"success": False, "message": f"Unable to create account: {exc}"}
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
