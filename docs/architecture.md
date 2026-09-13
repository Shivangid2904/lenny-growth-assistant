# Architecture: Lenny Growth Assistant

## 1. Overview

The **Lenny Growth Assistant** is a specialized, production-oriented assistant designed for product managers and growth professionals. It provides source-grounded answers to product and growth questions derived from *Lenny's Podcast* transcripts, transforms answers into structured long-form essays adhering to the **Ship 30 for 30** framework, and produces safely isolated Markdown and HTML/CSS artifacts.

This document defines the system architecture, data models, interaction protocols, and security boundaries. All architectural decisions documented here are locked for the implementation.

---

## 2. System Architecture

The application comprises three containerized services managed by Docker Compose, interfacing with an external cloud API (Anthropic Claude) and a host-managed local inference server (Ollama).

```
+-------------------------------------------------------------------------------+
|                                Host Machine                                   |
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   |                      Docker Compose Environment                       |   |
|   |                                                                       |   |
|   |   +----------------------+             +--------------------------+   |   |
|   |   |   Frontend Service   |  HTTP / SSE |     Backend Service      |   |   |
|   |   |   (React + Vite SPA) | <---------> |        (FastAPI)         |   |   |
|   |   |   Port: 3000         |             |        Port: 8000        |   |   |
|   |   +----------------------+             +-------------+------------+   |   |
|   |                                                      |                |   |
|   |                                                      | SQL / pgvector |   |
|   |                                                      v                |   |
|   |                                        +--------------------------+   |   |
|   |                                        |     Database Service     |   |   |
|   |                                        |  (pgvector/pgvector:16)  |   |   |
|   |                                        |        Port: 5432        |   |   |
|   |                                        +--------------------------+   |   |
|   +-----------------------------------------------------------------------+   |
|                                                          |                    |
|                                                          | HTTP               |
|                                                          v                    |
|   +------------------------------------+   +------------------------------+   |
|   |       Anthropic Cloud API          |   |      Host Ollama Service     |   |
|   |   (Configured Claude Model)        |   |  (nomic-embed-text, Ollama)  |   |
|   |   External Cloud Provider          |   |  http://host.docker.internal |   |
|   +------------------------------------+   +------------------------------+   |
+-------------------------------------------------------------------------------+
```

### Component Roles

1. **Frontend (React + Vite SPA):** Dual-pane interface (Chat and Sandboxed Artifact Viewer) handling user sessions, streaming SSE events, and isolated artifact rendering.
2. **Backend (FastAPI):** Exposes REST and SSE endpoints, orchestrates agent workflows via Claude Agent SDK (Python), performs vector search, and enforces security policies.
3. **Database (PostgreSQL + pgvector):** Consolidated persistence engine holding application state (sessions, messages, artifacts) and transcript vector embeddings.
4. **Host Ollama Server:** Generates local 768-dimensional text embeddings (`nomic-embed-text`) for ingestion/retrieval and serves the local reasoning model when local mode is active.
5. **Anthropic API:** Cloud LLM provider for reasoning and synthesis when cloud mode is active.

---

## 3. Data Layer

### Consolidated Storage Philosophy

PostgreSQL with the `pgvector` extension is selected as the sole persistence layer rather than maintaining a separate vector database (e.g., Pinecone, Qdrant).
- **Reduced Operational Complexity:** A single database simplifies local developer setup, backup routines, transactions, and container orchestration.
- **Corpus Sizing & Search Mechanics:** The MVP corpus contains ~20–30 podcast episodes (~2,000–4,000 chunks). At this scale, sequential scan using exact cosine distance (`<=>`) completes in sub-millisecond time.
- **Index Strategy:** No Approximate Nearest Neighbor (ANN) index (IVFFlat or HNSW) is created for MVP. Exact distance search avoids recall degradation and index build overhead. If the corpus scales beyond ~100,000 chunks, an HNSW index (`USING hnsw (embedding vector_cosine_ops)`) can be added without application redesign.

### Logical Schema

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Sessions Table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Messages Table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Transcript Chunks Table (Vector Storage)
CREATE TABLE transcript_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id VARCHAR(128) NOT NULL,
    episode_title VARCHAR(255) NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Artifacts Table
CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    type VARCHAR(32) NOT NULL CHECK (type IN ('markdown', 'html')),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    sanitized BOOLEAN DEFAULT TRUE NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indexes for relational navigation and session isolation
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_artifacts_session_id ON artifacts(session_id);
CREATE INDEX idx_transcript_chunks_episode ON transcript_chunks(episode_id);
```

### Session Isolation & Cascade Deletion

Session isolation is strictly enforced at the relational layer:
- Every query accessing messages or artifacts mandates a `WHERE session_id = :session_id` predicate.
- Foreign keys on `messages.session_id` and `artifacts.session_id` specify `ON DELETE CASCADE`. Removing a session automatically purges its conversational history and generated artifacts in a single atomic transaction.

---

## 4. Knowledge Ingestion & Retrieval

### Ingestion Flow

```text
Transcript Source (Text / Markdown)
    ↓
Select ~20–30 Representative Episodes
    ↓
Extract & Normalize Text (clean headers, remove timestamps, normalize whitespace)
    ↓
Chunk Transcripts (recursive character chunking: ~500–800 tokens, 100-token overlap)
    ↓
Generate 768-dim Embeddings via Host Ollama (model: nomic-embed-text)
    ↓
Store Chunks + Episode Metadata + Vector in PostgreSQL transcript_chunks
```

### Retrieval & Grounding Flow

```text
User Question / Topic
    ↓
Generate Query Embedding via Host Ollama (nomic-embed-text)
    ↓
Execute Cosine Similarity Search in PostgreSQL:
SELECT episode_id, episode_title, content, metadata,
       1 - (embedding <=> :query_embedding) AS similarity
FROM transcript_chunks
ORDER BY embedding <=> :query_embedding ASC
LIMIT :top_k;
    ↓
Check Similarity Against Relevance Threshold (e.g., similarity >= 0.70)
    ├─► If Below Threshold: Surface explicit refusal ("Not enough grounded information")
    └─► If Above Threshold: Pass chunks + metadata to Agent Reasoning Context
```

### Ingestion & Model Dependencies
- **Static Snapshot:** The MVP operates over a static snapshot of ingested episodes. Future updates rerun the ingestion script for newly added transcripts.
- **Local Embedding Invariant:** Embeddings are strictly generated locally via Ollama using `nomic-embed-text` (768 dimensions). Consequently, **Ollama must be running and accessible during ingestion**, even if Anthropic Claude is selected as the chat reasoning model.
- **Model Migration Trade-off:** Changing the embedding model in the future requires re-embedding all existing chunks and executing an `ALTER TABLE transcript_chunks ALTER COLUMN embedding TYPE vector(NEW_DIM)`.

---

## 5. Agent Layer

The agent is orchestrated using the **Claude Agent SDK (Python)** as a unified coordinator with three discrete, encapsulated skills.

```
                  +--------------------------------+
                  |     Claude Agent SDK           |
                  |     Orchestrating Agent        |
                  +---------------+----------------+
                                  |
         +------------------------+------------------------+
         |                        |                        |
         v                        v                        v
+------------------+    +--------------------+    +------------------+
| Grounded Q&A     |    | Ship 30 for 30     |    | Artifact         |
| Skill            |    | Skill              |    | Generation Skill |
+------------------+    +--------------------+    +------------------+
```

### 1. Grounded Q&A Skill
- **Purpose:** Answers user questions strictly using transcript content.
- **Responsibilities:**
  - Queries `transcript_chunks` using query embeddings.
  - Injects retrieved context into prompt templates with strict citation constraints.
  - Attributes every factual assertion to an episode title/identifier.
  - Halts and returns a standardized refusal message when retrieved similarity scores fail the threshold or when no chunks match.
  - Resolves multi-turn follow-ups by synthesizing recent session messages into a standalone search query before retrieval.

### 2. Ship 30 for 30 Skill
- **Purpose:** Converts grounded transcript advice into a structured long-form essay (~1,250 words) adhering to the Ship 30 for 30 writing framework.
- **Responsibilities:**
  - Ingests grounded transcript material (from prior chat turns or direct targeted retrieval).
  - Enforces the Ship 30 for 30 format:
    - **Headline & Hook:** Strong opening framing the core problem.
    - **Atomic Idea:** A single, sharp thesis statement.
    - **Structured Narrative:** Clear progressive sections with sub-headings (`H2`, `H3`).
    - **Scannability:** Frequent bullet points, numbered frameworks, and bold key terms.
    - **Actionable Takeaway:** Practical conclusion PMs can immediately implement.
  - Targets ~1,250 words (acceptable tolerance: 1,125–1,375 words).
  - Maintains strict factual grounding: all conceptual claims must originate from retrieved transcript material.
  - Exists as an encapsulated, deterministic skill rather than an ad-hoc system prompt tweak.

### 3. Artifact Generation Skill
- **Purpose:** Produces structured Markdown or standalone HTML/CSS documents.
- **Responsibilities:**
  - Formats content as either clean Markdown or self-contained HTML/CSS.
  - Treats all generated HTML as untrusted data.
  - Runs raw HTML through server-side sanitization prior to database persistence.
  - Persists the result into the `artifacts` table linked to the active session.

---

## 6. Model Provider Architecture

The backend implements a decoupled model client supporting a dual-provider toggle:

```
                          +-------------------------+
                          |   LLM Client Switch     |
                          |   (Config / Request)    |
                          +------------+------------+
                                       |
                   +-------------------+-------------------+
                   |                                       |
                   v                                       v
     +--------------------------+             +--------------------------+
     |   Anthropic Claude       |             |   Host Ollama            |
     |   (Cloud Provider)       |             |   (Local Provider)       |
     |   Configured via env     |             |   Configured via env     |
     +--------------------------+             +--------------------------+
```

### Provider Mechanics
- **Configuration Toggle:** Switched via environment configuration (`DEFAULT_LLM_PROVIDER=claude` or `ollama`) or optional request-level header/parameter.
- **Claude Client:** Communicates with Anthropic REST API using the official SDK and the configured `ANTHROPIC_API_KEY`. The specific cloud model is not hardcoded and is fully configurable through environment configuration (e.g., `ANTHROPIC_MODEL`).
- **Ollama Client:** Communicates with host Ollama HTTP endpoints (`/api/chat`, `/api/embeddings`) via `http://host.docker.internal:11434`, with the local reasoning model configured through environment configuration.
- **Fallback & Degradation:** If the active provider is unreachable or returns an error, the backend surfaces a structured error message (`MODEL_UNAVAILABLE` or `OLLAMA_UNAVAILABLE`) rather than crashing or silently failing.

---

## 7. API Contracts

All endpoints return JSON unless streaming via SSE. Errors always conform to the standard structured error envelope.

### Common Error Envelope

```json
{
  "error": {
    "code": "ERROR_CODE_STRING",
    "message": "Human-readable explanation of the error."
  }
}
```

#### Standard Error Codes
| Code | HTTP Status | Description |
| :--- | :--- | :--- |
| `VALIDATION_FAILED` | 422 | Request body or parameters failed schema validation |
| `SESSION_NOT_FOUND` | 404 | Specified session ID does not exist |
| `ARTIFACT_NOT_FOUND` | 404 | Specified artifact ID does not exist |
| `RETRIEVAL_EMPTY` | 200 / 404 | Retrieval found no matching transcript chunks |
| `MODEL_UNAVAILABLE` | 503 | Active LLM provider failed or is unreachable |
| `OLLAMA_UNAVAILABLE` | 503 | Host Ollama service is unreachable |
| `CLAUDE_NOT_CONFIGURED` | 503 | Anthropic API key is missing or blank |
| `MODEL_TIMEOUT` | 504 | Inference call exceeded configured timeout |
| `DATABASE_UNAVAILABLE` | 503 | PostgreSQL connection or query failure |
| `SANITIZATION_FAILED` | 500 | Artifact failed HTML sanitization or safety checks |

---

### Endpoints

#### 1. System Health
`GET /health`

Returns operational readiness of the service and downstream dependencies.

**Response (200 OK):**
```json
{
  "status": "ok",
  "dependencies": {
    "database": "up",
    "ollama": "up",
    "claude_api": "configured"
  }
}
```
*Health Semantics:*
- `database`: Live connection probe (`SELECT 1`).
- `ollama`: Live reachability check (`GET http://host.docker.internal:11434/api/tags`).
- `claude_api`: Configuration check verifying `ANTHROPIC_API_KEY` is present and non-empty. To avoid unnecessary latency and billing overhead, **no live inference request is made during health checks**.

---

#### 2. Configuration State
`GET /api/config`

Returns current runtime configuration and active model provider.

**Response (200 OK):**
```json
{
  "active_provider": "claude",
  "cloud_model": "configured-claude-model",
  "local_model": "configured-ollama-model",
  "embedding_model": "nomic-embed-text"
}
```

---

#### 3. Session Management

##### List Sessions
`GET /api/sessions`

**Response (200 OK):**
```json
[
  {
    "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "title": "B2B SaaS Pricing Discussion",
    "created_at": "2026-09-13T15:00:00Z",
    "updated_at": "2026-09-13T15:10:00Z"
  }
]
```

##### Create Session
`POST /api/sessions`

**Request Body (Optional):**
```json
{
  "title": "Growth Loops Exploration"
}
```

**Response (201 Created):**
```json
{
  "id": "b1ffca88-8d1c-4fe9-aa5e-5bb8bd380b22",
  "title": "Growth Loops Exploration",
  "created_at": "2026-09-13T15:15:00Z",
  "updated_at": "2026-09-13T15:15:00Z"
}
```

##### Get Session History
`GET /api/sessions/{id}`

**Response (200 OK):**
```json
{
  "id": "b1ffca88-8d1c-4fe9-aa5e-5bb8bd380b22",
  "title": "Growth Loops Exploration",
  "created_at": "2026-09-13T15:15:00Z",
  "updated_at": "2026-09-13T15:20:00Z",
  "messages": [
    {
      "id": "c2eedb77-7c2b-4de8-994d-4aa7ac270c33",
      "role": "user",
      "content": "How should an early-stage startup measure retention?",
      "created_at": "2026-09-13T15:16:00Z"
    },
    {
      "id": "d3ffea66-6b3a-4ce7-883c-3bb6ab160d44",
      "role": "assistant",
      "content": "According to Casey Winters in 'Scaling Growth Loops'...",
      "created_at": "2026-09-13T15:16:05Z"
    }
  ]
}
```

##### Delete Session
`DELETE /api/sessions/{id}`

**Response (204 No Content)**
*(Cascades deletion to all messages and artifacts associated with this session).*

---

#### 4. Chat & Streaming (SSE)

`POST /api/sessions/{id}/messages`

Submits a user message and streams the assistant response via Server-Sent Events (SSE).

**Request Body:**
```json
{
  "content": "What does Elena Verna say about Product-Led Sales?"
}
```

**Response Headers:**
```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

##### SSE Event Lifecycle & Event Types
1. **`token`**: Emitted sequentially as text chunks are generated by the model.
   ```text
   event: token
   data: {"delta": "Elena "}

   event: token
   data: {"delta": "Verna emphasizes "}
   ```
2. **`done`**: Emitted once generation finishes successfully. Contains the persisted assistant message ID and citations.
   ```text
   event: done
   data: {"message_id": "e4aabb55-5a4f-4ee6-772b-2aa5ba050e55", "citations": ["Elena Verna: The B2B Growth Engine"]}
   ```
3. **`error`**: Emitted if generation fails mid-stream.
   ```text
   event: error
   data: {"code": "MODEL_TIMEOUT", "message": "Inference request timed out."}
   ```

##### Persistence & Disconnection Invariant
- Assistant responses are persisted to PostgreSQL in a single write **only after the stream completes successfully** (upon reaching `done`). Tokens are not written to the database individually.
- If the client disconnects before stream completion, the session transaction aborts, and the partial message is **not** persisted as a completed assistant response.

---

#### 5. Ship 30 for 30 Essay Generation

`POST /api/sessions/{id}/skills/ship30`

Triggers the specialized Ship 30 for 30 skill.

**Request Body:**
```json
{
  "topic": "The PLG to Enterprise Transition",
  "source_context_message_ids": ["c2eedb77-7c2b-4de8-994d-4aa7ac270c33"]
}
```

**Response (201 Created):**
```json
{
  "artifact_id": "f5bbcc44-4b5e-4dd5-661a-1aa4ab940f66",
  "type": "markdown",
  "title": "Ship 30: The PLG to Enterprise Transition",
  "word_count": 1242,
  "content": "# The PLG Trap: Why Startups Fail at Enterprise Sales\n\n...",
  "created_at": "2026-09-13T15:25:00Z"
}
```

---

#### 6. Artifact Endpoints

##### Create Artifact
`POST /api/sessions/{id}/artifacts`

Generates an isolated document from current conversation context.

**Request Body:**
```json
{
  "type": "html",
  "title": "Growth Loop Framework Summary",
  "prompt": "Create a clean comparison table showing viral vs retention loops."
}
```

**Response (201 Created):**
```json
{
  "id": "f5bbcc44-4b5e-4dd5-661a-1aa4ab940f66",
  "session_id": "b1ffca88-8d1c-4fe9-aa5e-5bb8bd380b22",
  "type": "html",
  "title": "Growth Loop Framework Summary",
  "content": "<div class=\"framework-table\">...</div>",
  "sanitized": true,
  "created_at": "2026-09-13T15:26:00Z"
}
```

##### List Artifacts
`GET /api/sessions/{id}/artifacts`

**Response (200 OK):**
```json
[
  {
    "id": "f5bbcc44-4b5e-4dd5-661a-1aa4ab940f66",
    "type": "html",
    "title": "Growth Loop Framework Summary",
    "created_at": "2026-09-13T15:26:00Z"
  }
]
```

##### Get Artifact
`GET /api/sessions/{id}/artifacts/{artifact_id}`

**Response (200 OK):**
```json
{
  "id": "f5bbcc44-4b5e-4dd5-661a-1aa4ab940f66",
  "session_id": "b1ffca88-8d1c-4fe9-aa5e-5bb8bd380b22",
  "type": "html",
  "title": "Growth Loop Framework Summary",
  "content": "<div class=\"framework-table\">...</div>",
  "sanitized": true,
  "created_at": "2026-09-13T15:26:00Z"
}
```

---

## 8. Frontend Architecture

The frontend is a single-page application built with **React** and **Vite**, utilizing native React state primitives (`useState`, `useContext`) without third-party state managers (no Redux, Zustand, or MobX).

```
+-------------------------------------------------------------------------------+
|                                App Shell                                      |
|  [Header: Lenny Growth Assistant | Active Model: Anthropic Claude (Cloud)]    |
+---------------------------------------+---------------------------------------+
|              Chat Pane                |         Artifact Viewer Pane          |
|                                       |                                       |
| - Session List / Selector             | - Document Title & Metadata           |
| - Message History                     | - View Toggle (Markdown / HTML)       |
|   - User queries                      | - Rendered View:                      |
|   - Streamed assistant replies        |   - react-markdown (for Markdown)     |
|   - Citation tags [Ep: Title]         |   - Sandboxed <iframe> (for HTML)     |
| - Skill Action Bar:                   | - Word count indicator                |
|   [Generate Ship 30 Essay]            | - Copy / Export controls              |
|   [Create HTML Artifact]              | - Sanitization status badge           |
| - Message Input Box                   |                                       |
+---------------------------------------+---------------------------------------+
| Status / Error Bar: (Network, Refusal States, Reconnecting)                   |
+-------------------------------------------------------------------------------+
```

### Key Frontend Components & Behaviors
- **Chat Pane:** Handles session creation, switching, message input, and SSE event consumption via `EventSource` / `fetch` reader. Displays inline citation badges and explicit refusal cards.
- **Artifact Viewer Pane:** Displays artifacts alongside active chat. Supports Markdown formatting (`react-markdown` + `remark-gfm`) and sandboxed HTML rendering.
- **Model Indicator:** Always reflects the current provider (`Claude (Cloud)` or `Ollama (Local)`) retrieved via `GET /api/config`.
- **UI States:**
  - *Empty State:* Guidance on sample questions when a new session has no messages.
  - *Loading / Streaming State:* Pulsing cursor / progressive token rendering during generation.
  - *Refusal State:* Clear UI banner stating "No grounded transcript source found" rather than hallucinated answers.
  - *Error State:* Toasts and banners displaying structured backend error messages.
- **Responsive Layout:** Side-by-side view on desktop viewports; collapsible tabbed layout on smaller screens.

---

## 9. Security

### Untrusted HTML & Strict Isolation Strategy

All AI-generated HTML is treated as strictly untrusted user input. Rendering arbitrary HTML in a web application poses acute Cross-Site Scripting (XSS) risks, session hijacking, and DOM manipulation.

To completely prevent these attack vectors, the application enforces two security boundaries:

```text
Raw Model Output
    ↓
Server-Side HTML Sanitizer (bleach / ammonia equivalent)
[Strips <script>, removes inline event handlers (onclick, onload), enforces tag allowlist]
    ↓
Persisted in Database
    ↓
Transmitted to Frontend
    ↓
Rendered in Strict Sandboxed Iframe:
<iframe sandbox="allow-same-origin" srcdoc="..."></iframe>
(NEVER include allow-scripts)
```

### Sandboxing Guarantees
1. **No Script Execution:** `<iframe sandbox="allow-same-origin">` explicitly disallows script execution because `allow-scripts` is omitted. Even if a script bypasses the server-side sanitizer, the browser refuses to execute it.
2. **Blocked Event Handlers:** Inline handlers (`onclick`, `onerror`, `onload`, `javascript:`) are stripped by sanitization and inert inside the sandbox.
3. **Restricted Tag Allowlist:** Only structural and formatting tags are permitted (`div`, `span`, `p`, `h1`-`h6`, `table`, `thead`, `tbody`, `tr`, `td`, `th`, `ul`, `ol`, `li`, `b`, `i`, `strong`, `em`, `code`, `pre`, `blockquote`, `style`).
4. **No External Resource Exfiltration:** External scripts (`<script src="...">`) and external frame loading are blocked.
5. **No Parent Window Access:** The sandboxed iframe cannot access the parent window's `window`, `document`, `localStorage`, or `cookies`.

---

## 10. Error Handling & Observability

### Error Handling Paradigm
The system favors explicit, recoverable degradation over unhandled exceptions:
- **Empty Retrieval:** When vector distance fails the relevance threshold, the system returns a successful 200 payload containing an explicit refusal message ("I don't have enough grounded information to answer that based on available episodes") rather than a 500 error.
- **Database Disconnections:** Intercepted by FastAPI middleware, returning a structured `DATABASE_UNAVAILABLE` (503) error and emitting structured logs.
- **Provider Outages:** Unreachable Ollama or Anthropic endpoints surface `OLLAMA_UNAVAILABLE` or `MODEL_UNAVAILABLE` (503) with user-facing recovery hints.
- **Client Aborts:** Disconnected SSE streams log a warning, trigger agent cancellation, and abort uncommitted message transactions.

### Structured Observability
The backend logs all critical events in machine-readable JSON to stdout:
- **Context Fields:** `timestamp`, `session_id`, `request_id`, `endpoint`.
- **Model Logs:** `provider`, `model_name`, `prompt_tokens`, `completion_tokens`, `latency_ms`.
- **Retrieval Logs:** `query`, `chunks_retrieved`, `top_similarity_score`, `retrieval_latency_ms`.
- **Failure Logs:** `error_code`, `error_message`, `stack_trace` (for 5xx events).

No external SaaS observability tools (Datadog, Sentry) are introduced; standard container log collection (`docker compose logs`) captures all JSON records.

---

## 11. Deployment Topology

The entire system runs locally via **Docker Compose** on a developer workstation.

```text
Host Operating System
│
├── Ollama Service (Native / Host process on port 11434)
│   ├── nomic-embed-text (Embedding model)
│   └── llama3 (Local LLM reasoning model)
│
└── Docker Compose Network (bridge)
    ├── postgres (Container: pgvector/pgvector:pg16)
    │   └── Exposes port 5432 internally
    │
    ├── backend (Container: Python 3.11 / FastAPI)
    │   ├── Exposes port 8000 to host
    │   └── Connects to: postgres:5432, host.docker.internal:11434, Anthropic API
    │
    └── frontend (Container: Node 20 / Nginx or Vite dev)
        ├── Exposes port 3000 to host
        └── Connects to: backend:8000
```

### Service Communication
- The backend communicates with PostgreSQL via the Docker network using hostname `postgres`.
- The backend communicates with host-managed Ollama using `http://host.docker.internal:11434`.
- The backend communicates with Anthropic via outbound HTTPS.
- The frontend runs on port 3000 and proxies API requests to `http://localhost:8000`.

---

## 12. Key Trade-offs

| Decision | Trade-off / Limitation | Rationale |
| :--- | :--- | :--- |
| **pgvector without ANN Index** | O(N) sequential scan on every retrieval query. | The MVP corpus (~30 episodes, <5k chunks) makes brute-force scan instantaneous (<5ms) while avoiding the operational burden and index tuning of HNSW/IVFFlat. |
| **Local Ollama for Embeddings** | Ollama must be installed and active on the host machine even when Cloud Claude is selected for chat. | Eliminates embedding API costs, guarantees reproducible offline ingestion, and ensures identical embedding space for both local and cloud modes. |
| **Fixed 768-Dimension Column** | Changing the embedding model later requires a database schema migration and full corpus re-embedding. | Strong typing ensures data integrity and prevents corrupt mixed-dimension distance calculations in pgvector. |
| **Server-Sent Events (SSE) over WebSockets** | Unidirectional communication (server-to-client streaming only). | SSE runs over standard HTTP, natively supports auto-reconnection, works cleanly through reverse proxies without connection upgrades, and fits chat generation perfectly. |
| **Single Agent with Discrete Skills** | Sequential or rigidly defined routing rather than autonomous multi-agent swarms. | Predictable execution paths, bounded latency, deterministic costs, and straightforward debugging for an evaluation take-home. |
| **Strict Iframe Sandbox (No Scripts)** | HTML artifacts cannot execute JavaScript or render dynamic interactive charts (e.g., D3/Canvas). | Eliminates entire classes of XSS vulnerabilities; static HTML/CSS is completely sufficient for PM frameworks and documents. |
