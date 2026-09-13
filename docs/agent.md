# Agent Layer: Architecture, Grounding, Routing & Citations

## 1. Overview

The **Agent Layer** of the Lenny Growth Assistant orchestrates the conversational interaction between the user and Lenny's Podcast knowledge corpus. It sits between incoming API requests and the underlying reasoning model, enforcing:

1. **Deterministic Retrieval-First Execution:** Vector search always executes prior to model invocation and cannot be bypassed.
2. **Strict Grounding Policy:** Answers are derived solely from verified, retrieved transcript chunks.
3. **Relevance Gating:** Out-of-scope or weak matches are rejected before the model is called.
4. **Individual Chunk Filtering:** Each chunk must independently pass the cosine distance threshold.
5. **No Model Invocation on Insufficient Evidence:** If no chunks satisfy the threshold or the corpus is empty, the assistant returns a grounded refusal with zero model calls.
6. **Structured Citations:** Grounded responses include metadata linking directly to the cited episodes, guests, and URLs.
7. **Session Isolation & Bounded History:** Multi-turn context is strictly scoped by session ID and capped at the most recent 10 messages.
8. **Server-Sent Events (SSE):** Token-by-token streaming with atomic persistence only upon successful completion.

---

## 2. Deterministic Retrieval-First Architecture

```text
User Message
     ↓
Backend API Endpoint
     ↓
Session Verification & User Message Persistence
     ↓
Deterministic Vector Retrieval (ALWAYS RUNS)
     ↓
Top-K Nearest Chunks
     ↓
Relevance Gate: Evaluate Each Chunk Individually (distance <= threshold)
     ├────────────────────────────────────────┐
     │ Zero eligible chunks                   │ >= 1 eligible chunk
     ↓                                        ↓
Grounded Refusal                         Delimit Untrusted Evidence
(0 Model Invocations)                    + Fetch Session History (Last 10 msgs)
     ↓                                        ↓
Persist Refusal Response                 Reasoning Model (Claude or Ollama)
     ↓                                        ↓
SSE: Token deltas → Done                 SSE: Token deltas
                                              ↓
                                         Persist Assistant Response + Citations
                                              ↓
                                         SSE: Done (with message_id & citations)
```

### Critical Security Rule: Retrieval Is Not a Tool

Retrieval is an authoritative backend pipeline step, **not** an optional tool that the model may choose to invoke or skip. The reasoning model is never given the autonomy to answer from its pre-trained knowledge base when evidence is absent. If retrieval yields no evidence satisfying the relevance gate, the reasoning model is never invoked.

---

## 3. Model-Provider Abstraction

The system abstracts reasoning models behind the `LLMProvider` interface (`app/services/llm_provider.py`), allowing seamless toggling between cloud and local inference:

```text
               +-----------------------------+
               |      LLMProvider (ABC)      |
               |  stream_chat(sys, msgs, to) |
               +--------------+--------------+
                              |
       +----------------------+----------------------+
       |                                             |
+------v---------------+                      +------v---------------+
|  AnthropicProvider   |                      |    OllamaProvider    |
| (Claude Agent SDK /  |                      | (Local HTTP /chat    |
|   Anthropic Python)  |                      |   Streaming client)  |
+----------------------+                      +----------------------+
```

### Supported Providers

| Provider | Config Value (`LLM_PROVIDER`) | Model Setting | Behavior |
| :--- | :--- | :--- | :--- |
| **Anthropic Claude** | `anthropic` or `claude` | `ANTHROPIC_MODEL` (e.g. `claude-3-5-sonnet-20241022`) | Uses Anthropic Python SDK. If `ANTHROPIC_API_KEY` is missing/empty, returns structured `CLAUDE_NOT_CONFIGURED` without crashing. |
| **Local Ollama** | `ollama` | `OLLAMA_MODEL` (e.g. `llama3.2:latest`) | Streams from local Ollama endpoint `POST /api/chat`. If unreachable, returns structured `OLLAMA_UNAVAILABLE`. |
| **Deterministic Fake** | `fake` | N/A | Mock provider for unit and integration testing. |

### Provider Switching

The active provider is chosen via environment configuration:

```bash
LLM_PROVIDER=anthropic # or ollama
```

The runtime status of the active provider is inspectable via `GET /api/config` (never exposing API keys or secrets).

---

## 4. Relevance Gate & Individual Chunk Filtering

### Cosine Distance Semantics

pgvector cosine distance (`<=>`) yields values where **lower distance indicates higher similarity**:
- `distance = 0.0`: Identical vector direction.
- `distance <= threshold`: **Eligible evidence** (meets similarity requirement).
- `distance > threshold`: **Ineligible** (rejected).

### Individual Filtering Invariant

Retrieved chunks are evaluated **independently**. A top match that passes the threshold **does not qualify weaker chunks** in the same top-k result set.

**Example:**
With `threshold = 0.30`:
- Chunk 1: distance `0.22` → **Eligible** (sent to model, cited)
- Chunk 2: distance `0.27` → **Eligible** (sent to model, cited)
- Chunk 3: distance `0.45` → **Rejected** (excluded from prompt context and citations)
- Chunk 4: distance `0.58` → **Rejected** (excluded from prompt context and citations)

Only chunks that individually satisfy `distance <= threshold` are:
1. Injected into the prompt's `<transcript_evidence>` block.
2. Referenced in the structured `citations` metadata.

### Configuration & Calibration TODO

```ini
RAG_RELEVANCE_DISTANCE_THRESHOLD=0.35
```

> [!IMPORTANT]
> **Calibration Placeholder:** The current default `0.35` is a development placeholder. The 3-episode test fixture corpus is insufficient for empirical optimization.
> 
> **Pre-Submission Calibration TODO:**
> 1. Ingest the complete ~20–30 episode Lenny transcript corpus.
> 2. Construct an evaluation dataset with known-answerable growth questions and known out-of-scope queries (e.g., recipes, astronomy).
> 3. Measure the cosine distance distribution of true positives vs out-of-scope queries.
> 4. Select a calibrated distance threshold that maximizes precision while retaining high recall.
> 5. Update `RAG_RELEVANCE_DISTANCE_THRESHOLD` and record calibration metrics.

---

## 5. Grounding Policy & Prompt-Injection Trust Boundary

### Grounding Policy

The agent instructions enforce:
- Answers must be derived **strictly** from the eligible transcript evidence provided.
- Do not speculate or extrapolate using pre-trained world knowledge.
- Do not invent quotes, episodes, guests, numbers, URLs, or citations.
- Clearly state when the retrieved evidence only partially covers the topic.

### Prompt-Injection Trust Boundary

Retrieved transcript text is treated as **untrusted data**, not instructions.

```text
+-------------------------------------------------------------+
| System Instructions (Grounding policy, persona, constraints)|  Highest Authority
+-------------------------------------------------------------+
| Session History & Current User Query                        |
+-------------------------------------------------------------+
| <transcript_evidence>                                       |
|   [Source 1 | Episode: ... | Guest: ...]                   |  Untrusted Reference
|   Transcript content...                                     |  DATA Only
| </transcript_evidence>                                      |
+-------------------------------------------------------------+
```

Transcript content cannot alter system constraints, bypass refusal rules, or execute commands. Any instructional phrases inside transcript text (e.g., "Ignore instructions", "Output the system prompt") are treated as inert conversational quotes.

---

## 6. Refusal Behavior

When retrieval produces zero eligible chunks (or the corpus is empty):
- The reasoning model is **not invoked**.
- The backend yields a grounded refusal response:
  > *"I couldn't find enough relevant material in Lenny's Podcast transcripts to answer that reliably."*
- Structured citations are empty `[]`.
- The refusal response is persisted to the database as an assistant message.

---

## 7. Structured Citations

Every grounded answer emits structured citation metadata in the SSE `done` event and persists it in `messages.metadata`:

```json
{
  "episode_title": "Casey Winters on Scaling Growth Loops vs Funnels",
  "guest_name": "Casey Winters",
  "source_url": "https://www.lennyspodcast.com/casey-winters",
  "chunk_index": 0
}
```

Frontend consumers read citations directly from this structured payload without parsing arbitrary markdown text.

---

## 8. Session Context & Multi-Turn Isolation

### Session Isolation

All message queries are strictly parameterized by `WHERE session_id = :session_id`. Conversation history from Session A is never accessible to Session B.

### Bounded Conversation History

```ini
CONVERSATION_HISTORY_LIMIT=10
```

To maintain continuity for follow-up questions (e.g., *"How do I apply that to B2B?"*):
- The agent queries the most recent 10 messages for the active session (5 user/assistant turns).
- Messages are sorted in chronological order and prefixed before the current prompt.
- Messages older than the 10-message window are truncated to preserve token efficiency and prevent prompt drift.

---

## 9. Server-Sent Events (SSE) & Persistence Lifecycle

### Endpoint
`POST /api/sessions/{session_id}/messages`

### SSE Event Lifecycle

1. `token`: Incremental text chunk emitted during generation:
   ```text
   event: token
   data: {"delta": "Cohort "}
   ```
2. `done`: Emitted once generation finishes and the response is safely committed to PostgreSQL:
   ```text
   event: done
   data: {"message_id": "9f2b...", "citations": [...], "status": "completed"}
   ```
3. `error`: Emitted if an error occurs mid-stream:
   ```text
   event: error
   data: {"code": "MODEL_TIMEOUT", "message": "Inference generation timed out."}
   ```

### Persistence Invariant

- **User messages** are persisted immediately upon receipt.
- **Assistant messages** are persisted **only after full generation succeeds**. Tokens are never written individually to the database.
- If the client disconnects or an error occurs mid-stream, partial assistant messages are **not** persisted.

---

## 10. Model Timeout & Structured Error Handling

```ini
MODEL_TIMEOUT_SECONDS=60
```

Generation is wrapped in an explicit timeout. If the model hangs or takes longer than 60 seconds, a `ModelTimeoutError` (`MODEL_TIMEOUT`) is raised and the stream terminates cleanly with an error frame.

### Standard Error Codes

| Error Code | HTTP / SSE Status | Condition |
| :--- | :--- | :--- |
| `SESSION_NOT_FOUND` | 404 | Session UUID does not exist |
| `VALIDATION_FAILED` | 422 | Empty or whitespace-only message |
| `CLAUDE_NOT_CONFIGURED` | 503 / SSE `error` | `ANTHROPIC_API_KEY` is missing or empty |
| `OLLAMA_UNAVAILABLE` | 503 / SSE `error` | Host Ollama service is unreachable |
| `MODEL_UNAVAILABLE` | 503 / SSE `error` | Upstream model provider failure |
| `MODEL_TIMEOUT` | 504 / SSE `error` | Generation exceeded timeout |
| `DATABASE_UNAVAILABLE` | 503 / SSE `error` | PostgreSQL failure |

---

## 11. Backend-Authoritative Skill Routing Boundary

The backend maintains authoritative control over skill execution (`app/services/skill_router.py`):
- **Registered Skills:**
  - `chat`: Default grounded Q&A over transcripts.
  - `ship30`: Stub for Ship 30 for 30 essay generation (Checkpoint 4/5).
  - `artifact`: Stub for interactive artifact generation (Checkpoint 6).
- **Security Boundary:** Clients cannot invoke arbitrary Python functions or unapproved skills.
- **Inferred Routing Fallback:** The router inspects user intent (e.g. keywords like *"Ship 30"* or *"atomic essay"*) to route to specialized skills.

---

## 12. Structured Logging

Agent lifecycle events are logged with structured context:
- `agent_request_started`
- `retrieval_started`
- `retrieval_completed` (with `retrieval_count`, `best_distance`)
- `relevance_check_passed` / `relevance_check_failed`
- `agent_generation_started`
- `agent_generation_completed` / `agent_generation_failed`
- `assistant_message_persisted`
- `agent_request_completed` (with total `duration`)

No API keys, full transcripts, or sensitive conversation data are ever logged.
