# PRD: Lenny Growth Assistant

## 1. User & Problem

**Primary user:** Product managers and growth professionals who need quick, actionable guidance on product and growth questions grounded in Lenny's Podcast knowledge.

**Job to be done:** Get a trustworthy, sourced answer to a product/growth question without listening to hours of podcast episodes or manually searching transcripts — and turn that answer into reusable written content (an essay, a doc) without needing to write their own prompts.

**Problem removed:** Advice is scattered across hundreds of long-form transcripts. Finding the relevant passage, synthesizing across episodes, and converting it into something shareable currently takes manual search and prompt-crafting effort. The assistant collapses that into: ask → grounded answer with sources → optional generated artifact.

---

## 2. Success Metrics

**Primary — Grounded Answer Success Rate:**
Percentage of a fixed 15-question evaluation set (10 questions answerable from the ingested transcript subset, 5 deliberately out-of-scope/unanswerable) where the assistant either:
1. Gives a correct, source-cited answer, or
2. Correctly declines when the knowledge base doesn't support an answer.

*Evaluation Methodology:* Scored manually by the evaluator against expected ground-truth behavior and reported as a fraction in the test plan/README (e.g., "13/15").

**Secondary — Time-to-Usable-Artifact:**
For a subset of test questions, the number of user turns (not wall-clock time, which is model- and hardware-dependent) required to go from initial question to a rendered artifact (essay or Markdown/HTML doc) the user could plausibly use as-is. Lower is better; reported as a simple average across the test scenarios.

*(Rationale: Both metrics are concrete and measurable within a take-home evaluation timeframe without requiring live production traffic or A/B testing infrastructure.)*

---

## 3. Assumptions

Since the brief is intentionally incomplete, we make the following explicit assumptions:

- **Single Evaluator Context:** The app runs locally for an evaluator — no multi-tenant auth, SSO, or organization management is needed. A lightweight user identifier (e.g., a session-scoped UUID with no login requirement) is sufficient.
- **Static Knowledge Snapshot:** The transcript repository is treated as a static snapshot for the duration of the assignment; live re-ingestion or streaming freshness pipelines are not required, though the ingestion design will document how refreshes would operate.
- **Corpus Subset:** Ingesting a representative subset of episodes (e.g., ~20–30 episodes) is acceptable to demonstrate the end-to-end RAG pattern, provided this is explicitly documented as a scope decision.
- **Single Cloud Provider:** "Cloud LLM" requires only one working provider integration (Anthropic Claude), rather than multiple cloud providers with feature parity.
- **Local Machine Constraints:** The demo runs on a single developer machine with consumer-grade hardware. The local Ollama model choice is optimized to run comfortably within hardware constraints rather than matching cloud-scale parameter counts.
- **Sanitized Artifact Viewer:** The Artifact Viewer only needs to safely render Markdown and simple HTML/CSS. JavaScript execution is intentionally blocked via strict sandboxing (e.g., sandboxed `iframe`).
- **Data Leakage Scope:** The risk of "data leakage" is scoped to context isolation between distinct chat sessions (session isolation), rather than enterprise infrastructure-level data governance.

---

## 4. Scope

### In Scope (with explicit cuts)

- **Chat Interface & Sessions:** Web chat UI with new-session creation; each session maintains independent stored context backed by PostgreSQL.
- **Transcript Ingestion Pipeline:** Pipeline for a defined representative subset (~20–30 episodes), covering text extraction, chunking, and embedding generation, with documented instructions for scaling to additional episodes.
- **RAG Retrieval & Citations:** Semantic retrieval surfacing source citations (episode title/identifier) for every answer.
- **Conversation Grounding & Guardrails:** Multi-turn follow-up handling within active sessions, returning an explicit refusal message ("I don't have enough grounded information to answer that") when retrieval returns no relevant context above the threshold.
- **Model Toggle:** Configurable toggle between Anthropic Claude (cloud) and one Ollama-served model (local), with graceful fallback messaging if the selected provider is unavailable.
- **Ship 30 for 30 Skill:** A dedicated tool/skill (not an ad-hoc prompt) that converts grounded transcript answers into a structured ~1,250-word essay following Ship 30 for 30 writing framework principles (e.g., atomic idea, strong hooks, clear headings, bulleted takeaways).
- **Artifact Generation & Sandboxed Viewer:** Markdown and sanitized HTML/CSS generation rendered alongside the chat in an in-app Artifact Viewer, blocking script execution and unsafe tags/attributes.
- **Structured Observability:** Structured logging covering model calls, retrieval latency/results, database operations, and artifact rendering events.
- **Error Resilience:** Graceful failure handling and informative UI feedback for: missing API keys, unreachable Ollama instance, model request timeouts, empty retrieval results, and database connection failures.
- **Deployment:** Docker Compose setup for one-command local startup, with `.env.example` containing safe placeholder defaults.
- **Testing:** Automated tests for retrieval relevance, session isolation, and core API contracts, accompanied by a structured manual test plan for UI and artifact verification.

### Out of Scope (and rationale)

- **Full Transcript Corpus Ingestion:** Processing hundreds of episodes is unnecessary to prove the retrieval pattern and burns excessive local disk/compute; documented as a deliberate scope cut.
- **Multi-Cloud Parity:** Supporting multiple cloud LLM providers (e.g., OpenAI, Google Vertex) provides redundant signal beyond proving the dual cloud/local toggle architecture.
- **Full User Authentication & SaaS Features:** Multi-tenant orgs, RBAC, OAuth/SSO, user billing, and account management do not evaluate AI/growth systems engineering judgment.
- **Real-time Collaboration & Voice/Mobile:** Mobile layouts, voice input/transcription, and multi-user live sockets add complexity without addressing core assignment requirements.
- **Fine-Tuning / Distributed Systems:** Custom model fine-tuning, distributed task queues (e.g., Celery/Kafka), and multi-region database replication exceed the scope of a single-machine take-home.

---

## 5. Key User Flows

### Flow A — Grounded Q&A
1. User starts a new session.
2. User submits a product or growth question.
3. System searches vector embeddings for relevant transcript chunks.
   - If no chunks meet the relevance threshold: System responds with an explicit refusal ("I don't have enough grounded information to answer that based on available episodes").
   - If relevant chunks are found: System generates an answer citing the specific source episode(s).
4. User submits a follow-up question; system incorporates session history to maintain multi-turn context.

### Flow B — Ship 30 for 30 Essay Generation
1. User has an existing grounded answer in chat or requests an essay on a specific podcast topic.
2. User invokes the Ship 30 for 30 skill (via explicit command or prompt intent).
3. Skill retrieves and synthesizes grounded transcript content, structuring it strictly around Ship 30 for 30 principles to produce a ~1,250-word essay. Every substantive argument traces back to retrieved sources.
4. The essay renders in the dedicated Artifact Viewer panel rather than as an inline chat message.

### Flow C — Artifact Generation & Viewing
1. User requests a formatted document or HTML snippet based on the current discussion.
2. System generates Markdown or sanitized HTML/CSS.
3. The Artifact Viewer renders the content in a side-by-side pane.
4. Sanitization rules are applied (scripts stripped, unsafe elements neutralized); user receives visible indication if unsafe elements were removed.

### Flow D — Model Toggle
1. Evaluator selects the LLM provider (Anthropic Claude or local Ollama) via configuration or UI toggle.
2. System routes subsequent requests to the chosen provider.
3. If the active provider is unreachable or misconfigured, the system surfaces a clear error and fallback notice rather than failing silently.

---

## 6. Acceptance Criteria

- **Session Isolation:** A new chat session persists independently in PostgreSQL and does not leak conversation history or context across different session IDs.
- **Grounding Accuracy:** At least 10 of 15 evaluation questions produce accurate, source-cited responses; the 5 out-of-scope questions are explicitly declined rather than hallucinated.
- **Model Switching:** Switching between local Ollama and cloud Claude via configuration changes the inference provider without requiring application code changes, with the active model visibly indicated.
- **Ship 30 for 30 Fidelity:** Generated essays are within ±10% of 1,250 words (~1,125–1,375 words), feature clear formatting (headings, bullet points, bold emphasis), and ground every factual claim in retrieved transcript content.
- **Safe Artifact Sandbox:** Generated HTML artifacts cannot execute arbitrary JavaScript or invoke external scripts; verified by an automated test passing script injection payloads (`<script>`, inline `onload`/`onerror`).
- **Resilient Degradation:** Inducing failure states (stopping the PostgreSQL container, revoking an API key, or terminating Ollama) results in graceful, descriptive error responses in UI and structured logs without backend service crashes.
- **Turnkey Setup:** Running `docker compose up` from a fresh clone using only populated `.env.example` placeholders boots a fully operational backend, frontend, and database environment.

---

## 7. Risks & Trade-offs

| Risk | Mitigation Strategy |
| :--- | :--- |
| **Hallucination** | Enforce strict RAG grounding, set a relevance threshold for retrieval refusal, and mandate source citations on all claims. |
| **Response Latency** | Cap retrieved context token limits, enforce bounded max output tokens, and select a lightweight local model suitable for consumer hardware. |
| **Cloud Inference Cost** | Restrict cloud LLM execution to explicit Claude selection; avoid redundant multi-pass agent loops. |
| **Local Model Output Quality** | Document expected performance trade-offs compared to Claude; optimize local model choice for stability and instruction following on consumer devices. |
| **Cross-Session Data Leakage** | Isolate conversation histories strictly by session UUID at the database and memory layers; validate through automated multi-session test suites. |
| **Unsafe Artifact Rendering** | Employ strict HTML sanitization, sandboxed `iframe` rendering with `sandbox="allow-same-origin"`, and disallow script execution. |
| **Database & Provider Outages** | Implement explicit try/catch blocks with domain-specific exception handling, surfaced friendly error messages, and structured log events. |

---

## 8. Implementation Plan (High Level)

1. **Project Skeleton & Core Infrastructure:** Configure repository layout, Docker Compose, environment variables, and PostgreSQL schema.
2. **FastAPI Backend Services:** Establish health endpoints, session management, message persistence models, and API schemas.
3. **Transcript Ingestion & Vector Storage:** Build ingestion scripts for the selected episode subset; chunk transcripts, generate embeddings, and configure vector retrieval.
4. **Agent Orchestration & Model Provider Toggle:** Wire retrieval into context synthesis; implement model routing between Anthropic Claude and local Ollama with fallback handling.
5. **Ship 30 for 30 Skill:** Implement the structured essay generation tool grounded strictly in retrieved transcript passages.
6. **Artifact Generation & Sandboxed Viewer:** Build dual-panel UI supporting Markdown rendering and sandboxed HTML/CSS presentation.
7. **Resilience & Error Handling:** Implement error boundaries and graceful degradation for missing keys, connection drops, and empty search results.
8. **Testing & Documentation:** Execute automated test suites (retrieval quality, session isolation, XSS protection), assemble the 15-question evaluation benchmark, and author architecture, design, and runbook docs.
9. **Walkthrough & Verification:** Record demonstration video covering core user flows and edge case handling.
