# AdvocateAI

AdvocateAI is a legal-tech web platform built to help users find relevant lawyers faster using AI.

The project started as an AI-powered lawyer discovery tool and has now been extended toward a legal marketplace model where:

- clients can describe legal problems,
- AI can analyze issues and generate structured summaries,
- users can upload legal documents for AI analysis,
- clients can create cases,
- lawyers can view and respond to cases.

The current implementation extends the original codebase in-place without rewriting the project architecture from scratch.

## Live Access

- Public URL: http://159.89.163.233/
- Hosting: DigitalOcean

## Current Product Capabilities

### Core Platform

- User signup and login
- Persistent session handling in Flutter web
- Role-aware accounts:
  - client
  - lawyer
  - admin-ready database support
- AI chat for lawyer discovery
- Watchlist support for shortlisted lawyers

### AI Capabilities

- Semantic lawyer recommendation using Sentence Transformers embeddings
- Legal issue detection from free-text user queries
- Structured AI case analysis, including:
  - legal area
  - issue type
  - location
  - urgency
  - summary
- Legal document analysis for:
  - PDF files
  - image files (`jpg`, `jpeg`, `png`)
- AI-generated structured document analysis, including:
  - document type
  - legal area
  - key dates
  - summary
  - potential issue
  - recommended action

### Client Marketplace Flow

- Describe a legal problem via chat
- View an AI Case Analysis card
- Find recommended lawyers
- Create and save a legal case
- View personal cases

### Lawyer Marketplace Flow

- Create a lawyer profile
- Browse open cases
- View recommended cases
- Apply to cases
- View submitted applications

## Current Scope

- The seeded lawyer dataset is Germany-focused
- Current local demo/test data includes sample client, lawyer, case, and application records
- The system is prepared for broader legal workflows but not yet production-hardened in all areas

## Tech Stack

- Frontend: Flutter
- Backend: FastAPI (Python)
- Database: PostgreSQL
- AI: Gemini API + Sentence Transformers
- Hosting: DigitalOcean

## Architecture Overview

The project now uses a modular backend structure while keeping the existing app behavior intact.

### Backend

[backend/app.py](backend/app.py)
- FastAPI entrypoint
- CORS setup
- startup migrations
- router registration

[backend/db/database.py](backend/db/database.py)
- PostgreSQL connection setup
- startup migrations
- schema safety / backward-compatible table updates

[backend/routers/auth.py](backend/routers/auth.py)
- signup
- login

[backend/routers/chat.py](backend/routers/chat.py)
- AI chat endpoint
- legal issue detection
- lawyer recommendation payloads

[backend/routers/cases.py](backend/routers/cases.py)
- case creation
- client case listing
- open cases
- lawyer case recommendations
- case applications

[backend/routers/lawyers.py](backend/routers/lawyers.py)
- lawyer profile CRUD-style endpoints
- watchlist endpoints
- lawyer recommendation by case

[backend/routers/documents.py](backend/routers/documents.py)
- document upload analysis endpoint

[backend/services/ai_service.py](backend/services/ai_service.py)
- Gemini calls
- legal issue analysis
- structured JSON parsing
- chat generation helpers

[backend/services/matching_service.py](backend/services/matching_service.py)
- lawyer ranking logic using:
  - embedding similarity
  - legal area match
  - city match
  - language match
  - ratings

[backend/services/document_analysis_service.py](backend/services/document_analysis_service.py)
- PDF text extraction using `pdfplumber`
- image analysis flow for Gemini
- structured legal document analysis parsing

[backend/services/cache_service.py](backend/services/cache_service.py)
- cache placeholder for future Redis integration

[backend/services/integration_placeholders.py](backend/services/integration_placeholders.py)
- placeholders for:
  - push notifications
  - Stripe/payments
  - document storage
  - lawyer/client messaging expansion

### Frontend

[test_app/lib/main.dart](test_app/lib/main.dart)
- session-aware app entry
- role-based landing flow

[test_app/lib/home_page.dart](test_app/lib/home_page.dart)
- client dashboard
- AI chat UI
- case analysis card
- document upload analysis card
- premium navigation

[test_app/lib/client_cases_page.dart](test_app/lib/client_cases_page.dart)
- create case page
- my cases page
- recommended lawyers page

[test_app/lib/lawyer_dashboard_page.dart](test_app/lib/lawyer_dashboard_page.dart)
- lawyer dashboard
- lawyer profile
- open cases
- recommended cases
- applications

[test_app/lib/premium_page.dart](test_app/lib/premium_page.dart)
- pricing / premium UI
- no payment integration yet

## Project Structure

- `backend/`
  - `app.py`
  - `schema.sql`
  - `fetch_professionals.py`
  - `generate_embeddings.py`
  - `db/`
  - `models/`
  - `routers/`
  - `services/`
- `test_app/`
  - Flutter frontend
  - role-based screens
  - client/lawyer UI flows

## Database Design

### `users`
- `id`
- `name`
- `email`
- `password`
- `password_hash`
- `role`
- `created_at`

### `professionals`
- imported lawyer/professional dataset
- includes semantic embeddings used for recommendations

### `watchlist`
- saved professionals per user

### `lawyer_profiles`
- `lawyer_id`
- `name`
- `city`
- `practice_areas`
- `languages`
- `experience_years`
- `rating`
- `bio`
- `availability_status`

### `cases`
- `case_id`
- `client_id`
- `title`
- `description`
- `legal_area`
- `issue_type`
- `ai_summary`
- `urgency`
- `city`
- `created_at`
- `status`
- `is_public`

### `case_applications`
- `id`
- `case_id`
- `lawyer_id`
- `message`
- `created_at`
- `status`

### `messages`
- optional messaging-ready table for future case communication

## Quick Start

## 1. Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install fastapi uvicorn psycopg2-binary sentence-transformers pydantic python-dotenv requests pdfplumber python-multipart
```

Create `.env` inside `backend/`:

```env
GEMINI_API_KEY=your_key
GOOGLE_API_KEY=your_key
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres
```

## 2. Database + Data Setup

Run schema once:

```bash
psql -U postgres -d postgres -f schema.sql
```

Load professionals dataset:

```bash
python fetch_professionals.py
```

Generate embeddings:

```bash
python generate_embeddings.py
```

The app also runs startup migrations automatically through [backend/db/database.py](backend/db/database.py), so newer columns/tables are added safely when the API starts.

## 3. Start Backend

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Docs:

- http://127.0.0.1:8000/docs

## 4. Frontend Setup

```bash
cd test_app
flutter pub get
flutter run -d chrome
```

## Local Test Accounts

If demo data has been seeded locally, use:

- Client
  - username: `demo_client`
  - password: `demo123`
- Lawyer
  - username: `demo_lawyer`
  - password: `demo123`

## API Endpoints

### Auth

- `POST /signup`
- `POST /login`

### Chat / AI

- `POST /chat`

### Watchlist / Professionals

- `GET /watchlist/{user_id}`
- `POST /watchlist/add`
- `GET /professionals/{user_id}`

### Lawyer Profiles

- `POST /lawyer/profile`
- `GET /lawyer/profile/{lawyer_id}`

### Cases

- `POST /cases/create`
- `GET /cases/my?client_id={id}`
- `GET /cases/client/{client_id}`
- `GET /cases/open`
- `GET /cases/recommended/{lawyer_id}`
- `POST /cases/apply`
- `GET /cases/applications/{lawyer_id}`

### Recommendation Endpoint

- `GET /lawyers/recommended/{case_id}`

### Document Analysis

- `POST /documents/analyze`

Accepted file types:
- PDF
- JPG
- JPEG
- PNG

Response includes:
- `document_type`
- `legal_area`
- `key_dates`
- `summary`
- `potential_issue`
- `recommended_action`
- `recommended_lawyers`

## Current UI Screens

### Public
- landing page
- login page
- signup page

### Client
- home/dashboard
- AI legal issue chat
- document upload analysis card
- create case
- recommended lawyers
- my cases
- watchlist
- notifications
- premium/pricing page

### Lawyer
- lawyer dashboard
- lawyer profile
- open cases
- recommended cases
- applications

## Current Limitations

- Passwords are still stored in a simple form locally and should be replaced with proper hashing before production use
- CORS is currently permissive for development convenience
- Document analysis for images relies on Gemini image understanding rather than a full OCR pipeline
- Messaging, payments, document storage, and notifications are placeholder-ready but not fully implemented
- Flutter web currently uses web-specific config logic in [test_app/lib/config.dart](test_app/lib/config.dart)

## Roadmap / Next Improvements

- Production-safe password hashing and auth hardening
- Redis caching for repeated AI/matching lookups
- Stripe subscription/payment integration
- Push notifications
- Lawyer/client messaging UI
- Document upload persistence and storage
- Better lawyer profile filtering (availability, languages, expertise)
- Expanded legal dataset beyond Germany

## Notes for Development

- The codebase has been extended incrementally, not rewritten
- Existing endpoints and earlier user flows were preserved where possible
- New architecture is designed to support scaling into a client-lawyer marketplace cleanly

## Contact / Suggestions

If you would like to contribute or share suggestions:

**contact@visheshsrivastava.com**
