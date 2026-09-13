# Ship 30 for 30 Writing Skill & Content Generation

## 1. Overview & Purpose

The **Ship 30 for 30 Writing Skill** (`ship30`) is a backend-authoritative content-generation capability for the Lenny Growth Assistant. It enables the assistant to transform raw, retrieved transcript evidence from *Lenny's Podcast* into structured, publication-ready growth essays, social posts, and insights formatted according to modern digital writing principles.

Unlike unconstrained generative AI tools, the Ship30 skill operates under strict architectural constraints:
- It defines **HOW** content is presented (voice, narrative pacing, structure, formatting).
- It never dictates or invents **WHAT** facts are true (evidence must always originate from retrieved transcript chunks).
- It is backend-authoritative: clients cannot bypass routing or inject arbitrary skill execution.

---

## 2. Core Grounding Philosophy & Security

### Grounding Rules
1. **Zero Knowledge Bypass:** The Ship30 skill never bypasses deterministic RAG retrieval.
2. **Strict Evidence Confinement:** Factual claims about guests, companies, metrics, growth frameworks, and podcast conversations must derive solely from eligible chunks passing the cosine distance relevance threshold ($\le 0.35$).
3. **No Hallucinations:** The model is prohibited from inventing quotes, guest names, episode titles, statistics, or metrics.
4. **Direct Quotes Restricted:** Verbatim quotations from transcripts must be short (under 15 words). Synthesis and precise paraphrasing are preferred.
5. **Citations Preserved:** All grounded outputs link back to their source episodes and guest metadata.
6. **Refusal on Empty Evidence:** If retrieval yields no chunks meeting the relevance threshold, the system immediately returns a grounded refusal without invoking the reasoning model.

### Prompt Injection & Untrusted Data Boundary
Transcripts represent untrusted third-party content. All retrieved transcript excerpts are enclosed within explicit `<transcript_evidence>` security boundaries. The system prompt explicitly instructs the reasoning model to treat text inside transcript tags strictly as reference data, preventing prompt injection attacks from overriding system instructions, routing logic, or word count contracts.

---

## 3. Supported Content Types & Contracts

The Ship30 skill supports four distinct content types:

| Content Type ID | Format | Target Length / Volume | Primary Use Case |
|---|---|---|---|
| `essay` | Long-form Ship 30 for 30 Essay | **~1,250 words** (Accepted range: **1,125 – 1,375 words**) | In-depth strategic growth lessons, frameworks, case studies |
| `linkedin` | LinkedIn Post | 150 – 300 words | Hook-driven, skimmable professional posts with high whitespace |
| `thread` | X / Twitter Thread | 5 – 10 numbered posts (240–280 chars each) | Sequential narrative breakdown of a podcast insight |
| `insight` | Concise Growth Insight | 80 – 150 words | Single tight paragraph answering an operational product question |

> [!IMPORTANT]
> The **1,125–1,375 word** requirement applies strictly to the **GENERATED ESSAY OUTPUT** produced by the model. It does not constrain the length of the Python skill definition or prompt metadata.

---

## 4. Writing Principles

The skill encodes core Ship 30 for 30 principles:

### Ideation & Structure
- **One Clear Idea:** Anchor the piece around a single central thesis stated in the opening.
- **Strong Hook:** Open with a striking observation, counterintuitive data point, or palpable tension.
- **Reader-Oriented Framing:** Write directly to the reader (product managers, growth practitioners, founders).
- **Deliberate Narrative Progression:** Move cleanly through: Hook $\rightarrow$ Thesis $\rightarrow$ Evidence $\rightarrow$ Practical Implications $\rightarrow$ Actionable Takeaways.

### Prose Style
- **Short, Declarative Sentences:** Avoid winding sentences; aim for punchy clarity under ~25 words.
- **Rhythmic Variety:** Alternate short punches with explanatory synthesis and concrete examples.
- **Concrete Specificity:** Favor granular examples ("retention curves flattening at Month 3") over abstractions ("good retention").
- **Zero Fluff / Anti-Padding:** Every sentence must earn its place. Do not pad prose to reach word targets.

### Formatting & Visual Structure
- **Short Paragraphs:** 2–4 sentences per block. Single-sentence paragraphs used deliberately for punchiness.
- **Markdown Headings (`##` / `###`):** Divide long-form essays into distinct, readable phases.
- **Selective Bolding:** Bold key terms sparingly (1–2 per section) to aid scanning without visual noise.
- **Judicious Bullet Lists:** Use lists only when presenting 3+ parallel items; never substitute lists for coherent prose.

---

## 5. Content-Type Structural Guidelines

### Long-Form Essay (~1,250 words)
Approximate Section Word Budgets (summing to ~1,200–1,300 words):
1. **Opening Hook + Setup (~120–140 words):** Compelling tension or counterintuitive claim grounded in the podcast topic; outlines the problem space.
2. **Thesis & Framework Overview (~150–170 words):** Central thesis introducing the framework and explaining why product-market fit cannot be isolated.
3. **Fit 1: Market-Product Fit (~140–160 words):** Transcript-grounded exploration of market demand, audience dynamics, and product value proposition.
4. **Fit 2: Product-Channel Fit (~140–160 words):** Grounded analysis of distribution channels, virality, and why products are built to fit channels.
5. **Fit 3: Channel-Model Fit (~140–160 words):** Grounded analysis of monetization model, ARPU, and channel CAC constraints.
6. **Fit 4: Model-Market Fit (~140–160 words):** Grounded analysis of pricing model, market size, and customer volume required for viability.
7. **Why Startups Fail: Breakdown of Interlocking Fits (~180–200 words):** 2–4 concrete failure modes and diagnostic signals when fits change asynchronously.
8. **Practical Takeaways & Concluding Playbook (~180–200 words):** Actionable evaluation framework resolving the opening hook and tension.

### LinkedIn Post (150–300 words)
1. **Hook:** First 1–2 lines optimized for before the "see more" fold.
2. **Core Insight:** The primary takeaway in 1 concise paragraph.
3. **Evidence:** 1–2 grounded data points or examples from Lenny's guests.
4. **Takeaway:** Immediate operational conclusion.
5. **CTA:** Non-generic discussion prompt.

### X / Twitter Thread (5–10 posts)
1. **1/: Hook Tweet:** Standalone claim driving interest.
2. **2/–4/: Evidence Tweets:** Numbered breakdowns of transcript-backed insights.
3. **5/–7/: Nuance / Case Studies:** Real-world examples or counter-cases.
4. **8/–9/: Practical Lessons:** Tactical advice for builders.
5. **Final Tweet:** Summary takeaway linking back to the opening hook.

### Concise Insight (80–150 words)
A single tightly-edited paragraph: Thesis $\rightarrow$ Explanation $\rightarrow$ Transcript Evidence $\rightarrow$ Practical Action.

---

## 6. Backend-Authoritative Skill Routing

Routing decisions are made entirely on the backend in `app/services/skill_router.py` using explicit patterns defined in `app/skills/ship30.py`. The frontend cannot pass arbitrary execution parameters or force arbitrary skills.

### Routing Table
| Intent Pattern / Trigger | Routed Skill | Routed Content Type |
|---|---|---|
| `"ship 30 for 30"` / `"ship30 for 30"` | `ship30` | `essay` |
| `"ship 30 essay"` / `"ship30 essay"` | `ship30` | `essay` |
| `"atomic essay"` | `ship30` | `essay` |
| `"1,250-word essay"` / `"1250-word essay"` | `ship30` | `essay` |
| `"write a growth lesson"` | `ship30` | `essay` |
| `"linkedin post"` / `"turn this into a post"` | `ship30` | `linkedin` |
| `"twitter thread"` / `"x thread"` / `"tweet thread"` | `ship30` | `thread` |
| `"concise product insight"` / `"growth insight"` | `ship30` | `insight` |
| `"ship 30"` / `"ship30"` (generic) | `ship30` | `essay` (default) |
| Standard product questions (e.g. "What is PMF?") | `chat` | `None` |

Conversational questions without explicit formatting triggers route to the default `chat` skill, ensuring the system remains natural and responsive for standard Q&A.

---

## 7. Verification & Testing

The Ship30 skill is backed by comprehensive test coverage:
- **Unit & Contract Tests (`tests/test_ship30.py`):** 66 tests covering:
  - Skill metadata and supported content types
  - Pattern detection and case-insensitivity
  - Fallback behaviors and parameter validation
  - Word count boundary contract enforcement (1,125–1,375 words)
  - Structural elements (headings, paragraphs, closings)
  - Grounding instructions and prompt injection boundaries
  - End-to-end routing integration
- **Full Backend Test Suite:** 111 / 111 tests passing.
- **Live Verification (`verify_ship30_live.py`):** End-to-end execution against the real 15-episode Lenny corpus in PostgreSQL, running through Ollama (`nomic-embed-text` for retrieval and `llama3.2` for generation).
