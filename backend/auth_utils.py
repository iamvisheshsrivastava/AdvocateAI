import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from logging_config import get_logger

logger = get_logger(__name__)

# Render sets RENDER=true on every deployed service, regardless of whether an
# ENVIRONMENT/ENV var has been configured, so it's used as an extra signal on
# top of an explicit ENVIRONMENT/ENV var to decide whether we're running in a
# real deployment (production-like) or a local/dev/test setup.
_ENVIRONMENT = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).strip().lower()
_IS_PRODUCTION = bool(os.getenv("RENDER")) or _ENVIRONMENT in {"production", "prod"}

_SECRET = os.getenv("JWT_SECRET_KEY")
if not _SECRET:
    if _IS_PRODUCTION:
        raise RuntimeError(
            "JWT_SECRET_KEY environment variable must be set in production. "
            "Refusing to start with no configured JWT signing secret."
        )
    # Local/dev fallback only: a random secret generated fresh for this
    # process. Never a hardcoded literal, and never used in production.
    _SECRET = secrets.token_urlsafe(32)
    logger.warning(
        "JWT_SECRET_KEY is not set; using a random per-process secret for "
        "local development. Existing tokens will be invalidated on restart. "
        "Set JWT_SECRET_KEY before deploying to production."
    )

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


def decode_token(token: str) -> dict:
    """Decode and validate a raw JWT string.

    Used by transports (e.g. WebSockets) that can't rely on the
    ``HTTPBearer``/``Depends`` machinery used for regular HTTP routes.
    Raises ``HTTPException(401, ...)`` if the token is missing/invalid.
    """
    return _decode(token)
