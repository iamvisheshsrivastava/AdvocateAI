# Contributing to AdvocateAI

Thanks for your interest in contributing. AdvocateAI is a FastAPI backend paired with a Flutter frontend; this guide covers how to get both running locally, how to test your changes, and how to submit a pull request.

## New to the project?

Look for issues labeled [`good first issue`](https://github.com/iamvisheshsrivastava/AdvocateAI/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) — these are small, well-scoped tasks (a validation fix, a missing test, a UI polish) that come with enough context to start without having to learn the whole codebase first.

## Project layout

```
backend/        FastAPI app (app.py), routers/, models/ (Pydantic request models),
                 services/ (business logic), db/ (connection pooling)
test_app/       Flutter frontend (lib/), targets Chrome/web
tests/          Backend pytest suite (runs against backend/ via tests/conftest.py)
requirements.txt  Pinned Python dependencies for the backend
```

## Setting up the dev environment

### Backend (FastAPI)

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r ..\requirements.txt
```

Create a `.env` file inside `backend/` with your local database and API settings. The repository's `.env.example` (used for the production Docker Compose stack) lists the full set of variables this project understands, including:

- `DATABASE_URL` (or discrete `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD`)
- `REDIS_URL` (or discrete `REDIS_HOST` / `REDIS_PORT`)
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_VISION_MODEL` — only needed if you're working on AI-powered features (chat, case analysis, document intelligence); most backend code paths have non-LLM fallbacks and will still run without a key
- `LLM_DEFAULT_TIMEOUT`, `LLM_ANALYSIS_TIMEOUT`, `LLM_BRIEF_TIMEOUT`, `LLM_CHAT_TIMEOUT`, `LLM_DOCUMENT_TIMEOUT`

You don't need a production Postgres/Redis instance to contribute to most backend logic — many services and routers degrade gracefully (see `backend/routers/auth.py`'s local-JSON-file fallback for signup/login when the database is unreachable) — but for full end-to-end testing, point `DATABASE_URL`/`DB_*` at a local Postgres instance and apply `backend/schema.sql`.

Run the backend:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Once it's up, check `http://localhost:8000/health` — it reports both database and LLM connectivity, which is the fastest way to tell "the server process started" apart from "the server can actually talk to its dependencies."

### Frontend (Flutter)

```bash
cd test_app
flutter pub get
flutter run -d chrome
```

By default the frontend talks to the backend via `ApiConfig.baseUrl` (see `test_app/lib/config*.dart`); make sure your local backend is running on the expected host/port, or adjust the config for your setup.

## Running tests

### Backend tests (pytest)

From the **repository root** (not `backend/`) — `tests/conftest.py` adds `backend/` to `sys.path`:

```bash
pip install -r requirements.txt
pytest
```

CI (`.github/workflows/deploy.yml`) runs plain `pytest` from the repo root after installing `requirements.txt`, so that's the command your changes need to pass. Add new tests under `tests/`, following the existing style in files like `tests/test_feature_hardening.py` and `tests/test_issue_fixes.py` (small, focused tests that import directly from `backend/` modules, using `fastapi.testclient.TestClient` for router-level tests and `monkeypatch` to avoid hitting a real database or LLM).

### Frontend tests (Flutter)

```bash
cd test_app
flutter test
```

Existing tests live in `test_app/test/` (e.g. `widget_test.dart`, `case_workspace_page_test.dart`).

## Code style

There's no enforced linter/formatter config committed for either side, so match the conventions already in the file you're editing:

- **Python**: standard FastAPI/Pydantic style — typed request/response models in `backend/models/`, business logic in `backend/services/`, thin routers in `backend/routers/`. Use `logging_config.get_logger(__name__)` for logging rather than `print`. Favor explicit `Field(..., min_length=..., max_length=...)` constraints on Pydantic models over ad-hoc validation in route handlers.
- **Dart/Flutter**: standard Flutter widget conventions as seen in `test_app/lib/` (`StatefulWidget` + `State` classes, `theme.dart` for shared colors/typography). Keep network calls in small top-level helper functions (see `loginUser`/`signupUser` in `login_page.dart`/`signup_page.dart`) rather than inline in widget build methods.
- Keep changes focused and minimal — prefer a small, reviewable diff over a large speculative refactor, especially for a first contribution.

## Submitting a pull request

1. Fork the repo and create a branch off `main` for your change.
2. Make your change, and add/update tests that cover it (`pytest` for backend, `flutter test` for frontend).
3. Make sure `pytest` (from the repo root) and, if you touched the Flutter app, `flutter test` (from `test_app/`) both pass locally.
4. Open a pull request against `main` with a clear description of what changed and why. Reference the issue number if your PR closes one (e.g. "Closes #38").
5. Be responsive to review feedback — small, incremental follow-up commits are fine.

If you're unsure whether an approach is right before investing time in it, feel free to open an issue or comment on an existing one first.
