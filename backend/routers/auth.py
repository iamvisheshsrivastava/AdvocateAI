from fastapi import APIRouter
from db.database import get_db_connection
from models.user import LoginRequest, SignupRequest

router = APIRouter(tags=["auth"])


def _normalize_role(role: str | None) -> str:
    normalized = (role or "client").strip().lower()
    if normalized in ("client", "lawyer", "admin"):
        return normalized
    return "client"


@router.post("/login")
async def login(data: LoginRequest):
    username = data.username.strip()
    password = data.password.strip()

    if not username or not password:
        return {"success": False}

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

    if not user:
        return {"success": False}

    return {
        "success": True,
        "user_id": user[0],
        "username": user[1],
        "email": user[2],
        "role": user[3],
    }


@router.post("/signup")
async def signup(data: SignupRequest):
    username = data.username.strip()
    password = data.password.strip()
    role = _normalize_role(data.role)

    if not username or not password:
        return {"success": False, "message": "Username and password are required."}

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE LOWER(name) = LOWER(%s)", (username,))
    existing = cur.fetchone()

    if existing:
        cur.close()
        conn.close()
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
    cur.close()
    conn.close()

    return {"success": True, "user_id": user_id, "username": username, "role": role}
