from datetime import datetime, timezone
import logging
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from db.database import get_db_connection, run_startup_migrations
from errors import AppError
from logging_config import configure_logging, get_logger
from routers.auth import router as auth_router
from routers.chat import router as chat_router
from routers.cases import router as cases_router
from routers.documents import router as documents_router
from routers.lawyers import router as lawyers_router
from routers.legal_actions import router as legal_actions_router
from routers.messages import router as messages_router
from routers.notifications import router as notifications_router
from routers.realtime import router as realtime_router

configure_logging()
logger = get_logger(__name__)

app = FastAPI(title="AdvocateAI API", version="2.0")
app_started_at = datetime.now(timezone.utc)


def _csv_env(name: str, default: str = "") -> list[str]:
    raw_value = os.getenv(name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _optional_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    return value.strip() if value and value.strip() else None


app.add_middleware(
    CORSMiddleware,
    allow_origins=_csv_env(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost,http://127.0.0.1,http://localhost:8000,http://127.0.0.1:8000",
    ),
    allow_origin_regex=_optional_env("CORS_ALLOW_ORIGIN_REGEX", r"http://(localhost|127\.0\.0\.1)(:\d+)?"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    try:
        run_startup_migrations()
    except Exception as exc:
        logger.exception("Startup migrations skipped: %s", exc)


def _check_database_connection() -> tuple[bool, str | None]:
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        return True, None
    except Exception as exc:
        if conn is not None:
            conn.close()
        logger.exception("Database connection check failed")
        return False, str(exc)


app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(cases_router)
app.include_router(lawyers_router)
app.include_router(documents_router)
app.include_router(legal_actions_router)
app.include_router(messages_router)
app.include_router(notifications_router)
app.include_router(realtime_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("Validation error: %s %s", request.url, exc)
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("Application error on %s: %s", request.url, exc.message)
    content = {"detail": exc.message}
    if exc.details is not None:
        content["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error handling request %s", request.url)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.get("/")
async def health():
    return {"status": "ok", "service": "AdvocateAI"}


@app.get("/health")
async def health_details():
    from services.ai_service import GEMINI_API_KEY, AI_CONFIG
    db_ok, db_error = _check_database_connection()

    # Quick Gemini connectivity probe (cheap: tiny prompt, short timeout)
    gemini_ok = False
    gemini_error = None
    if GEMINI_API_KEY:
        try:
            import requests as _req
            model = AI_CONFIG.gemini_model
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={GEMINI_API_KEY}"
            )
            resp = _req.post(
                url,
                json={"contents": [{"parts": [{"text": "ping"}]}]},
                timeout=8,
            )
            resp.raise_for_status()
            gemini_ok = True
        except Exception as exc:
            # Sanitize: strip the API key from the URL in error messages
            raw = str(exc)
            if GEMINI_API_KEY:
                raw = raw.replace(GEMINI_API_KEY, "***")
            gemini_error = raw
    else:
        gemini_error = "GEMINI_API_KEY not configured"

    overall_ok = db_ok and gemini_ok
    payload = {
        "status": "ok" if overall_ok else "degraded",
        "service": "AdvocateAI",
        "version": app.version,
        "started_at": app_started_at.isoformat(),
        "uptime_seconds": max(0, int((datetime.now(timezone.utc) - app_started_at).total_seconds())),
        "database": {"ok": db_ok, "error": db_error},
        "gemini": {"ok": gemini_ok, "model": AI_CONFIG.gemini_model, "error": gemini_error},
    }
    return JSONResponse(status_code=200 if db_ok else 503, content=payload)
