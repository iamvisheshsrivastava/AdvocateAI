# AdvocateAI

AdvocateAI is an AI-powered legal-tech platform that helps people understand legal problems, analyze legal documents, find relevant lawyers, and move toward consultation through a marketplace-style flow.

It combines:
- AI legal issue detection
- AI document analysis
- AI intake readiness scoring and consultation prep
- legal action guidance for official government workflows
- lawyer recommendation
- client case creation
- lawyer case discovery and applications
- secure client-lawyer messaging
- explainable lawyer matching
- notification-driven marketplace workflows

## What the App Does

### For Clients
- sign up and log in
- describe a legal problem in natural language
- get an AI case analysis
- receive a Legal Action Guide for supported common scenarios
- upload a PDF or image document for legal analysis
- capture multi-page document packets before upload
- find recommended lawyers
- save a problem as a case
- view personal cases
- maintain a lawyer watchlist
- message lawyers inside a case workspace
- view structured case briefs and timelines
- review missing intake information, deadline signals, and consultation questions

### For Lawyers
- create a lawyer profile
- browse open cases
- view recommended cases
- apply to cases
- review submitted applications
- set availability status
- track responsiveness metrics
- message clients inside case workspaces

## Key Features

- AI chat-based lawyer discovery
- semantic lawyer matching
- Legal Action Guide with official portal links and required information checklists
- explainable lawyer matching with match reasons
- role-based client/lawyer flows
- case marketplace workflow
- legal document analysis for PDF and image uploads
- case intelligence cards with readiness score, missing-info prompts, risk flags, and key dates
- Redis-backed optional caching and AI rate limiting
- structured case briefs stored on cases
- notifications for applications, messages, and recommendations
- secure case messaging and timeline events
- responsive Flutter web UI

## Screenshots

The screenshots below are captured from the current seeded demo build so they reflect the latest client, lawyer, and notification flows.

### Landing Page
![Landing Page](assets/screenshots/landing-page.png)

### Login Page
![Login Page](assets/screenshots/login-page.png)

### Client Dashboard
![Client Dashboard](assets/screenshots/client-dashboard.png)

### Create Case Page
![Create Case Page](assets/screenshots/create-case-page.png)

### Lawyer Dashboard
![Lawyer Dashboard](assets/screenshots/lawyer-dashboard.png)

### Notifications Center
![Notifications Center](assets/screenshots/notifications-page.png)

## Tech Stack

- Frontend: Flutter
- Backend: FastAPI
- Database: PostgreSQL
- AI: Gemini API + Sentence Transformers

## Local Run

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r ..\requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
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
REDIS_HOST=localhost
REDIS_PORT=6379
```

Redis is optional. If it is unavailable, AdvocateAI falls back to in-memory caching and local rate limiting.

### Frontend

```bash
cd test_app
flutter pub get
flutter run -d chrome
```

## Demo Login

### Client
- Username: `demo_client`
- Password: `demo123`

### Lawyer
- Username: `demo_lawyer`
- Password: `demo123`

## Main Capabilities in the Current Build

- signup / login
- persistent session handling
- AI legal issue analysis with Germany-aware disclaimers, confidence, and recommended actions
- AI-powered intake readiness report with missing information, follow-up questions, risk flags, and consultation prep
- Legal Action Guide for lost phone, consumer complaint, tenant dispute, and employment complaint scenarios
- AI document upload analysis for single or multi-file packets
- workspace-level case intelligence that updates alongside timelines and key dates
- lawyer recommendations with explainable match reasons and availability filtering
- watchlist
- case creation and listing with structured case briefs
- lawyer profile management with availability and responsiveness scoring
- case applications
- secure case messaging and timeline tracking
- notification center for client and lawyer workflows
- premium pricing UI placeholder

## Current Scope

- current professional dataset is focused on Germany-based lawyers
- the app is structured to scale into a larger legal marketplace
- payments and durable document storage are not fully implemented yet

## Status

AdvocateAI is currently a working prototype / early product foundation for an AI-assisted legal marketplace.

## Contact

**contact@visheshsrivastava.com**
