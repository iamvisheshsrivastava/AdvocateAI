import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

_SECRET = os.getenv("JWT_SECRET_KEY", "advocateai-dev-secret-change-in-production")
_ALGORITHM = "HS256"
_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "168"))  # 7 days

_bearer = HTTPBearer(auto_error=False)


def create_access_token(user_id: int, role: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(user_id), "role": role, "email": email, "exp": expire},
        _SECRET,
        algorithm=_ALGORITHM,
    )


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return _decode(credentials.credentials)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    if credentials is None:
        return None
    try:
        return _decode(credentials.credentials)
    except HTTPException:
        return None
