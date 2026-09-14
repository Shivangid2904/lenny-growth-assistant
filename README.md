# Lenny Growth Assistant

A production-ready, grounded growth assistant built on Lenny Rachitsky's podcast transcripts. The system combines deterministic transcript retrieval (RAG via PostgreSQL + pgvector), strict evidence-based grounding, backend-authoritative skills (Ship 30 for 30 writing and interactive Artifact generation), and a real-time React chat interface with a sandboxed artifact previewer.

---

## System Architecture

```
                               ┌───────────────────────────────────────────────┐
                               │           Client Browser (User)               │
                               └───────┬───────────────────────────────▲───────┘
                                       │ HTTP / REST                   │ SSE Streaming
                                       ▼                               │
                       ┌───────────────────────────────┐               │
                       │     Frontend (Nginx / Vite)   │               │
                       │     - Port: 3000 (Docker)     │               │
                       │     - Port: 5173 (Dev)        │               │
                       │     - Secure Iframe Sandbox   │               │
                       └───────────────┬───────────────┘               │
                                       │ Reverse Proxy (/api, /healthz)│
                                       ▼                               │
                       ┌───────────────────────────────┐               │
                       │     Backend API (FastAPI)     │───────────────┘
                       │     - Port: 8000              │
                       │     - Alembic Migrations      │
                       │     - Agent & Skills Orchestr.│
                       └───────┬───────────────┬───────┘
                               │               │
           Vector Similarity   │               │ Provider Selection
           & Session History   ▼               ▼ (Local vs. Cloud)
  ┌───────────────────────────────┐   ┌───────────────────────────────┐
  │  PostgreSQL 16 + pgvector     │   │   LLM Generation Provider    │
  │  - transcript_chunks (768-d)  │   │   - Ollama (llama3.2:latest)  │
  │  - sessions                   │   │   - Anthropic Claude 3.5      │
  │  - messages                   │   │   - Ollama (nomic-embed-text) │
  │  - artifacts                  │   └───────────────────────────────┘
  └───────────────────────────────┘
```

---

## Key Features

1. **Strict Transcript Grounding & Refusals**:
   - Queries are embedded using `nomic-embed-text` (768 dimensions) and matched against cosine distance thresholds calibrated on real podcast transcripts.
   - Grounded refusals are treated as **successful** assistant responses (`done` event with `citations: []`), not system errors.
   - Robust prompt-injection boundaries protect against adversarial transcript content.

2. **Backend-Authoritative Skills**:
   - **Ship 30 for 30 Writing Skill**: Generates structured essays (1,125–1,375 words), LinkedIn posts, X threads, and concise insights following Ship 30 frameworks.
   - **Artifact Generation Skill**: Generates interactive HTML, SVG diagrams, and Mermaid charts, persisted in PostgreSQL and rendered safely.

3. **Defense-in-Depth Artifact Security**:
   - Rendered inside a sandboxed iframe (`sandbox="allow-same-origin"`, strictly **omitting** `allow-scripts` and `allow-top-navigation`).
   - Restrictive Content Security Policy (`default-src 'none'; style-src 'unsafe-inline' ...`).
   - Zero `dangerouslySetInnerHTML` usage across the frontend codebase.

4. **Production Operability**:
   - Standard `/healthz` lightweight liveness probe (no external dependencies).
   - Detailed `/health` readiness probe (checks PostgreSQL connectivity and LLM provider reachability).
   - Configurable CORS via `CORS_ALLOWED_ORIGINS` (JSON array format).
   - Multi-stage Docker containers with automatic Alembic migrations on startup.

---

## Quick Start with Docker Compose (Recommended)

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose v2+
- Running Ollama instance on your host (if using local provider):
  ```bash
  ollama pull llama3.2:latest
  ollama pull nomic-embed-text
  ```

### Step 1: Environment Configuration
Copy the example environment file:
```bash
cp .env.example .env
```

If you plan to use Anthropic Claude instead of local Ollama, update `.env`:
```env
ACTIVE_LLM_PROVIDER=cloud
ANTHROPIC_API_KEY=your_sk_ant_key_here
```

### Step 2: Build and Run Services
Launch all services (PostgreSQL, FastAPI Backend, and Nginx Frontend) in detached mode:
```bash
docker compose up --build -d
```

### Step 3: Access the Application
- **Frontend Chat Interface**: `http://localhost:3000`
- **Backend API & Swagger Docs**: `http://localhost:8000/docs`
- **Liveness Probe**: `http://localhost:8000/healthz`
- **Readiness Probe**: `http://localhost:8000/health`

### Step 4: Verify Services Status
```bash
docker compose ps
```
All containers (`lenny_postgres`, `lenny_backend`, `lenny_frontend`) will report `healthy`.

---

## Manual Host Setup (Local Development)

### 1. PostgreSQL with pgvector
Start a local PostgreSQL instance with `pgvector` enabled:
```bash
docker run -d --name lenny_postgres -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgrespassword \
  -e POSTGRES_DB=lenny_growth \
  pgvector/pgvector:pg16
```

### 2. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Alembic database migrations
alembic upgrade head

# Start FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite development server (proxies /api to localhost:8000)
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## LLM Provider Setup

### Option A: Local LLM with Ollama (Default & Free)
1. Install [Ollama](https://ollama.ai).
2. Pull required models:
   ```bash
   ollama pull llama3.2:latest
   ollama pull nomic-embed-text
   ```
3. Set environment variable:
   ```env
   ACTIVE_LLM_PROVIDER=local
   OLLAMA_BASE_URL=http://localhost:11434
   ```
   *Note*: When running in Docker Compose, the backend communicates with Ollama on your host via `http://host.docker.internal:11434`.

### Option B: Cloud LLM with Anthropic Claude
1. Obtain an API key from the [Anthropic Console](https://console.anthropic.com/).
2. Set environment variables:
   ```env
   ACTIVE_LLM_PROVIDER=cloud
   ANTHROPIC_API_KEY=sk-ant-api03-...
   CLOUD_MODEL_NAME=claude-3-5-sonnet-20241022
   ```

---

## Ingesting & Refreshing Podcast Transcripts

To ingest transcripts and compute embeddings:

```bash
cd backend
python -m ingestion.scripts.ingest_transcripts \
  --input-dir ../data/transcripts \
  --batch-size 50
```

To run calibration and evaluation on RAG retrieval:
```bash
python -m ingestion.scripts.evaluate_retrieval \
  --eval-set ../data/eval_questions.json
```

---

## Frontend Build-Time Variable Note

> [!IMPORTANT]
> **Vite build-time configuration**: In Vite applications, all environment variables prefixed with `VITE_` (such as `VITE_API_BASE_URL`) are embedded directly into the compiled JavaScript bundle at **build time** (`npm run build` or during `docker build`).
>
> They **cannot** be modified dynamically at container runtime. If you change `VITE_API_BASE_URL`, you must rebuild the frontend container:
> ```bash
> docker compose build frontend
> docker compose up -d frontend
> ```

---

## Server-Sent Events (SSE) Streaming Contract

The assistant streams responses via `/api/sessions/{session_id}/messages` using SSE:

| Event | Purpose | Example Payload |
|---|---|---|
| `token` | Streamed text delta | `{"delta": "According to Brian Balfour..."}` |
| `done` | Successful completion (including grounded refusals) | `{"message_id": "...", "citations": [...], "status": "completed", "skill": "chat", "artifact": null}` |
| `error` | System / infrastructure failure | `{"code": "PROVIDER_ERROR", "message": "Ollama service unavailable"}` |

### Grounded Refusal Semantics
When retrieved transcript chunks fall below the relevance threshold, the assistant returns a polite, grounded refusal through the **`done`** event with `citations: []`. This indicates successful policy enforcement rather than a system failure. The `error` event is reserved strictly for operational faults (e.g., database disconnects, provider timeouts).

---

## Testing & Quality Assurance

### Backend Automated Test Suite
Includes 137 tests covering database models, Alembic migrations, retrieval math, RAG calibration, agent routing, Ship30 generation, artifact creation, SSE streaming, CORS headers, and health probes:

```bash
cd backend
pytest tests/ -v
```

### Frontend Automated Test Suite
Includes 28 Vitest tests covering ChatComposer, ChatMessage, useChat SSE hook, and ArtifactViewer security attributes:

```bash
cd frontend
npm test -- --run
```

### Frontend Production Build Validation
```bash
cd frontend
npm run build
```

---

## Production Deployment Guide (Platform-Neutral)

To deploy the Lenny Growth Assistant in production environments (e.g., AWS ECS/EKS, Google Cloud Run, Render, Fly.io):

1. **Database**:
   - Provision a managed PostgreSQL 16+ instance with the `vector` extension enabled (`CREATE EXTENSION IF NOT EXISTS vector;`).
   - Run migrations using `alembic upgrade head`.

2. **Backend**:
   - Deploy `backend/Dockerfile` as a web service.
   - Set environment variables:
     - `DATABASE_URL`: Connection string to production PostgreSQL.
     - `ACTIVE_LLM_PROVIDER`: `cloud` (recommended for production) or `local`.
     - `ANTHROPIC_API_KEY`: Production API key.
     - `CORS_ALLOWED_ORIGINS`: JSON array of production frontend domains (e.g., `["https://assistant.example.com"]`).
     - `APP_ENV`: `production`.
   - Point orchestration healthchecks to `/healthz` (liveness) and `/health` (readiness).

3. **Frontend**:
   - Build `frontend/Dockerfile` with `ARG VITE_API_BASE_URL=/api` (if using reverse proxy) or `https://api.example.com` (if on a separate domain).
   - Terminate TLS/HTTPS at your cloud load balancer (e.g., AWS ALB, Cloudflare, or Traefik).

---

## Known Limitations

1. **Vite Build-Time Config**: As documented, `VITE_API_BASE_URL` cannot be dynamically injected at container runtime without rebuilding the frontend bundle.
2. **TLS / HTTPS**: The repository configurations serve HTTP on ports 8000 and 3000. In production, TLS termination should be handled by an ingress controller, API gateway, or cloud load balancer.
3. **Host-Bound Ollama**: In Docker Compose, Ollama runs on the host machine to leverage GPU acceleration without complex container passthrough.
4. **Authentication**: The API endpoints are currently unauthenticated, designed as a single-tenant take-home demonstration. Production multi-tenancy requires adding user authentication (e.g., OAuth2 / JWT).