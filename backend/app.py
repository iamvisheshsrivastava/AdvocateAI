from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import run_startup_migrations
from routers.auth import router as auth_router
from routers.chat import router as chat_router
from routers.cases import router as cases_router
from routers.documents import router as documents_router
from routers.lawyers import router as lawyers_router
from routers.legal_actions import router as legal_actions_router
from routers.messages import router as messages_router
from routers.notifications import router as notifications_router

app = FastAPI(title="AdvocateAI API", version="2.0")

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
