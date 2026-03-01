# AdvocateAI

AdvocateAI is a legal-tech platform that helps users discover the most relevant lawyer quickly using AI-powered semantic search.

Instead of only keyword matching, AdvocateAI understands user intent from natural language questions and recommends suitable legal professionals by combining expertise context, reviews, ratings, and city data.

## Live Access

- Public URL: http://159.89.163.233/
- Deployment: Hosted on a DigitalOcean server

## What It Does

- User authentication (Sign Up / Login)
- Persistent session handling (users stay logged in after refresh)
- AI chat-based legal professional discovery
- Watchlist support for shortlisted professionals
- Clean landing page and user flow for web/mobile

## Current Scope

- The current dataset is focused on Germany-based lawyers.
- Expansion to additional countries, legal domains, and richer digital legal workflows is in progress.

## Planned Improvements

I am actively planning to add more features, including:

- Stronger profile filtering (practice area, language, availability)
- Better personalization and recommendation quality
- Improved production security (password hashing, stricter CORS, env-based credentials)
- Broader legal coverage beyond the current Germany-first scope

## Tech Stack

- Frontend: Flutter
- Backend: FastAPI (Python)
- Database: PostgreSQL
- AI: Sentence Transformers + Gemini API

## Project Structure

- `backend/` — FastAPI APIs, data ingestion, embeddings, schema
- `test_app/` — Flutter web/mobile frontend

## Quick Start

### Backend

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

Run setup + backend:

```bash
psql -U postgres -d postgres -f schema.sql
python fetch_professionals.py
python generate_embeddings.py
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd test_app
flutter pub get
flutter run -d chrome
```

## Main API Endpoints

- `POST /signup`
- `POST /login`
- `POST /chat`
- `GET /watchlist/{user_id}`
- `GET /professionals/{user_id}`
- `POST /watchlist/add`

## Contribute / Suggestions

If you would like to contribute or share suggestions, feel free to email:

**contact@visheshsrivastava.com**
