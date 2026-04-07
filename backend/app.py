from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from db.database import get_db_connection, run_startup_migrations
from routers.auth import router as auth_router
from routers.chat import router as chat_router
from routers.cases import router as cases_router
from routers.documents import router as documents_router
from routers.lawyers import router as lawyers_router
from routers.legal_actions import router as legal_actions_router
from routers.messages import router as messages_router
from routers.notifications import router as notifications_router

app = FastAPI(title="AdvocateAI API", version="2.0")
app_started_at = datetime.now(timezone.utc)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    run_startup_migrations()


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
        return False, str(exc)


app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(cases_router)
app.include_router(lawyers_router)
app.include_router(documents_router)
app.include_router(legal_actions_router)
app.include_router(messages_router)
app.include_router(notifications_router)


@app.get("/")
async def health():
    return {"status": "ok", "service": "AdvocateAI"}


@app.get("/health")
async def health_details():
    db_ok, db_error = _check_database_connection()
    payload = {
        "status": "ok" if db_ok else "degraded",
        "service": "AdvocateAI",
        "version": app.version,
        "started_at": app_started_at.isoformat(),
        "uptime_seconds": max(0, int((datetime.now(timezone.utc) - app_started_at).total_seconds())),
        "database": {
            "ok": db_ok,
            "error": db_error,
        },
    }
    return JSONResponse(status_code=200 if db_ok else 503, content=payload)
