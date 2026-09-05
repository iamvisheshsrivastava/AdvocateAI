# AdvocateAI

AdvocateAI is an AI-assisted legal marketplace prototype that helps people understand a legal issue, review documents, prepare a case, and connect with relevant lawyers in one flow.

The current build is focused on making the first steps of legal help easier: understanding the problem, organizing the case, and starting communication between clients and lawyers.

## Main Functionality

- AI chat to understand a legal problem in plain language
- AI case analysis with a simple summary, urgency signals, and next-step guidance
- document upload and analysis for PDFs and images
- document batch storage with follow-up question answering over uploaded files
- structured extraction for parties, deadlines, amounts, obligations, and risks
- document Q&A retrieval so follow-up questions can be answered against previously uploaded files
- legal action guidance for supported common situations
- lawyer recommendations based on the case details
- case creation, case tracking, and case workspace collaboration
- client-lawyer messaging inside the case workspace
- notifications for messages, applications, and recommendations
- separate client and lawyer experiences

## Tech Stack

**Backend & APIs:** FastAPI, Python, Uvicorn  
**Embeddings & Matching:** [fastembed](https://github.com/qdrant/fastembed) (ONNX build of `all-MiniLM-L6-v2`, ~100 MB instead of pulling in the full PyTorch/sentence-transformers stack) — vectors are stored as JSON arrays in PostgreSQL and compared with a plain NumPy dot product. No dedicated vector database; the case/lawyer volume here doesn't justify running Qdrant or FAISS yet, and this keeps the deploy footprint small enough to fit a free-tier instance  
**Document parsing:** `pdfplumber` and `pymupdf` for PDF text/page extraction, sent through the LLM for structured extraction  
**LLM Provider:** OpenRouter — currently `z-ai/glm-4.6` for text and `z-ai/glm-4.6v` for document image analysis (both free-tier; see [Free-Tier Deployment](#free-tier-deployment) for why the model id matters and how to change it)  
**Frontend:** Flutter (Dart), Chrome target  
**Infrastructure:** Docker, Git, Linux  

## Architecture Overview

1. User uploads a legal document (PDF or image)
2. Text is extracted (`pdfplumber`/`pymupdf`) and, for follow-up Q&A, embedded with fastembed and stored alongside the document row in Postgres
3. On a follow-up question, the query is embedded the same way and matched against stored document embeddings via cosine/dot-product similarity — a straightforward in-process search rather than a separate retrieval service
4. Extracted text and retrieved context are passed to the LLM (via OpenRouter) with a structured prompt asking for a specific JSON shape
5. The LLM's response is parsed into a case summary, extracted entities (parties, deadlines, amounts, obligations, risks), urgency signals, and next-step guidance

This is intentionally simple. There's a `_build_llamaindex_index` hook in `document_intelligence_service.py` left over from an earlier attempt at wiring in LlamaIndex for retrieval, but `llama-index` isn't in `requirements.txt` and the hook is stubbed to return `None` — worth knowing if you're reading the code and wondering why it's there. The numpy-dot-product approach it replaced turned out to be enough for the current scale.

## What Clients Can Do

- sign up and log in
- describe a legal problem and get AI guidance
- upload one or more legal documents for analysis
- receive a case summary and intake-readiness insights
- ask follow-up questions against the uploaded document batch
- view suggested lawyers for their issue
- create and manage cases
- keep a lawyer watchlist
- chat with lawyers inside a case workspace
- follow case updates, key dates, and timeline activity

## What Lawyers Can Do

- sign up and manage a lawyer profile
- set availability and maintain profile details
- browse open cases
- view recommended cases
- apply to client cases
- review case details before responding
- message clients in the shared workspace
- track activity through dashboard and notifications

## Current Scope

- the current dataset is centered on Germany-based lawyers and legal flows
- the app already supports an end-to-end prototype experience for discovery, case intake, and lawyer connection
- uploaded document batches are stored for later Q&A and retrieval-based follow-up
- some areas are still early-stage, including payments and long-term production storage workflows

## Screenshots

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

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r ..\requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Create a `.env` file inside `backend/` with the required database and API key settings.

Once the backend is running, you can verify service and database readiness at `http://localhost:8000/health` — it also reports whether the configured OpenRouter model is actually reachable, which is the fastest way to tell "the backend is up" apart from "the backend is up but the LLM call will fail." The root `/` route still returns a lightweight OK response.

### Frontend

```bash
cd test_app
flutter pub get
flutter run -d chrome
```

## Docker Production Deployment

This repository includes a Docker-based production stack:

- `frontend`: Flutter web served by Nginx, with `/api` proxied to the backend
- `backend`: FastAPI served by Uvicorn
- `db`: PostgreSQL 16
- `redis`: Redis for cache and rate limiting

Create a production env file from the committed example:

```bash
cp .env.example .env.production
```

Fill in the real values, especially `DB_PASSWORD`, `OPENROUTER_API_KEY`, `PUBLIC_APP_URL`, `PUBLIC_API_BASE_URL`, and `CORS_ALLOWED_ORIGINS`.

Run the stack on the server:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

View service status:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

The GitHub Actions pipeline in `.github/workflows/deploy.yml` runs backend tests, validates the Docker Compose config, syncs the repository to the DigitalOcean droplet, writes `.env.production` from GitHub Secrets, and starts the Docker stack.

Required GitHub Secrets:

- `DO_HOST`
- `DO_SSH_KEY`
- `DB_PASSWORD`
- `OPENROUTER_API_KEY`
- `PUBLIC_APP_URL`
- `PUBLIC_API_BASE_URL`
- `CORS_ALLOWED_ORIGINS`

Optional GitHub Secrets:

- `DO_USER` defaults to `root`
- `DO_DEPLOY_PATH` defaults to `/root/AdvocateAI`
- `DB_NAME` defaults to `advocateai`
- `DB_USER` defaults to `advocateai`
- `CORS_ALLOW_ORIGIN_REGEX`
- `LOG_LEVEL`
- `OPENROUTER_MODEL`
- `OPENROUTER_VISION_MODEL`
- `LLM_DEFAULT_TIMEOUT`
- `LLM_ANALYSIS_TIMEOUT`
- `LLM_BRIEF_TIMEOUT`
- `LLM_CHAT_TIMEOUT`
- `LLM_DOCUMENT_TIMEOUT`

## Free-Tier Deployment

The backend can also run entirely on free-tier managed services instead of a DigitalOcean droplet:

- **Backend**: [Render](https://render.com) free web service — configured via [`render.yaml`](render.yaml) (Blueprint). Deploys automatically from `main`.
- **Database**: [Neon](https://neon.tech) serverless Postgres — set `DATABASE_URL` on Render.
- **Cache**: [Upstash](https://upstash.com) serverless Redis — set `REDIS_URL` on Render.
- **LLM**: [OpenRouter](https://openrouter.ai) free-tier models — set `OPENROUTER_API_KEY` on Render.
- **Frontend**: [Cloudflare Pages](https://pages.cloudflare.com), connected to this repo, building `test_app/` with Flutter.

Render's free instance spins down after inactivity (cold start ~30-50s on the next request). Check backend health at `/health`, which reports database and LLM connectivity.

**Live deployment:**
- Frontend: https://advocateai-1va.pages.dev
- Backend API: https://advocateai-backend.onrender.com (health: `/health`)

## Demo Login

### Client
- Username: `demo_client`
- Password: `demo123`

### Lawyer
- Username: `demo_lawyer`
- Password: `demo123`

## Status

AdvocateAI is currently a working prototype for an AI-assisted legal help and lawyer-matching platform.

## Contact

**contact@visheshsrivastava.com**
