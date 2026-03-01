# AdvocateAI

AdvocateAI is a legal-tech app to help users find the right lawyer quickly using AI-based semantic search.

## Project Structure

- `backend/` — FastAPI + PostgreSQL API
- `test_app/` — Flutter web/mobile app

## Main Features

- User Sign Up / Login
- Session persistence (stay logged in after refresh)
- AI chat to find relevant legal professionals
- Watchlist management
- Clean landing page + auth flow

## Tech Stack

- **Frontend:** Flutter
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL
- **AI:** Sentence Transformers + Gemini API

## Quick Start

### 1) Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install fastapi uvicorn psycopg2-binary sentence-transformers pydantic python-dotenv requests
```

Create `.env` in `backend/`:

```env
GEMINI_API_KEY=your_key
GOOGLE_API_KEY=your_key
```

Initialize DB and run setup scripts:

```bash
psql -U postgres -d postgres -f schema.sql
python fetch_professionals.py
python generate_embeddings.py
```

Start backend:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend

```bash
cd test_app
flutter pub get
flutter run -d chrome
```

## API (Main)

- `POST /signup` — create account
- `POST /login` — login user
- `POST /chat` — semantic legal search chat
- `GET /watchlist/{user_id}` — user watchlist
- `GET /professionals/{user_id}` — available professionals
- `POST /watchlist/add` — add professionals to watchlist

## Notes

- Current setup is development-focused.
- Move DB credentials and all secrets to environment variables for production.
- Restrict CORS and use proper password hashing before production.
