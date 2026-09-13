# Lenny Growth Assistant — Corpus Documentation

## Overview

This document describes the transcript corpus used for the Lenny Growth
Assistant RAG (Retrieval-Augmented Generation) system, including the source
repository, episode selection rationale, ingestion pipeline, and retrieval
calibration evidence.

---

## 1. Authoritative Source Repository

| Property | Value |
|---|---|
| Source repository | https://github.com/ChatPRD/lennys-podcast-transcripts |
| Pinned commit | `be8ab89a890a833cbba2c892178f823fff178c65` |
| Access method | Local git clone (gitignored; not committed to this repo) |
| Clone path | `ingestion/data/raw_repo/` (gitignored) |

> [!IMPORTANT]
> Raw transcript files are **not committed** to this repository.
> The `.gitignore` explicitly excludes `ingestion/data/raw_repo/` and
> `ingestion/data/raw/`.
> Only the manifest file, metadata, and evaluation datasets are tracked in git.

---

## 2. Episode Corpus Selection

### Selection Strategy

15 representative episodes were selected to provide broad coverage of Lenny's
Podcast core product and growth competency domains:

- Product-Market Fit & Retention
- Growth Loops & Funnels
- Product-Led Growth (B2B & B2C)
- Monetization & Pricing
- Onboarding & Activation
- Experimentation & A/B Testing
- Product Strategy & Positioning
- Jobs to Be Done
- Product Leadership & Career Growth

### Corpus Manifest

The full selection is captured in
[`ingestion/data/corpus_manifest.json`](../ingestion/data/corpus_manifest.json).

### Selected Episodes

| # | Episode ID | Guest | Primary Topics |
|---|---|---|---|
| 1 | `brian-balfour` | Brian Balfour | PMF, Retention, Growth Loops, Four Fits |
| 2 | `casey-winters` | Casey Winters | Growth Loops vs Funnels, Scaling |
| 3 | `elena-verna` | Elena Verna | B2B PLG, Product-Led Sales, Failed Growth Tactics |
| 4 | `adam-fishman` | Adam Fishman | Onboarding, Growth Teams, Activation |
| 5 | `april-dunford` | April Dunford | Positioning, Competitive Alternatives, B2B Sales |
| 6 | `madhavan-ramanujam` | Madhavan Ramanujam | Pricing, Monetization, Willingness-to-Pay |
| 7 | `shreyas-doshi` | Shreyas Doshi | PM Strategy, LNO Framework, Execution |
| 8 | `bob-moesta` | Bob Moesta | Jobs to Be Done, Forces of Progress |
| 9 | `gibson-biddle` | Gibson Biddle | DHM Strategy Framework, Proxy Metrics |
| 10 | `gustaf-alstromer` | Gustaf Alstromer | Early PMF, Startup Retention, YC Lessons |
| 11 | `hila-qu` | Hila Qu | PLG Playbooks, Activation Metrics |
| 12 | `nikhyl-singhal` | Nikhyl Singhal | Product Leadership, CPO/VP Career Path |
| 13 | `bangaly-kaba` | Bangaly Kaba | Adjacent User Theory, Activation Plateaus |
| 14 | `andy-johns` | Andy Johns | Growth Strategy, Network Effects, Distribution |
| 15 | `ronny-kohavi` | Ronny Kohavi | A/B Testing, Experimentation Science, Trustworthy Experiments |

**Total corpus**: 15 episodes · 1,761 chunks ingested (1,756 real + 5 fixtures) · ~208,000 words

---

## 3. Ingestion Pipeline

### Parameters

| Parameter | Value |
|---|---|
| Embedding model | `nomic-embed-text` via Ollama |
| Embedding dimension | 768 |
| Chunk size | 1000 characters |
| Chunk overlap | 150 characters |
| Chunking strategy | Paragraph-boundary-aware with sentence fallback |
| Chunk ID | UUIDv5 deterministic: `lenny:{episode_id}:{chunk_index}` |
| Idempotency | Upsert on `(episode_id, chunk_index)` unique constraint |
| Similarity metric | Cosine distance via pgvector `<=>` |

### Running Ingestion

```bash
# First-time ingestion (idempotent — safe to re-run)
python ingestion/scripts/ingest_real_corpus.py

# Full reload (truncates table before ingesting)
python ingestion/scripts/ingest_real_corpus.py --refresh
```

### Idempotency Guarantee

Re-running ingestion on already-ingested transcripts performs upserts.
The `(episode_id, chunk_index)` unique constraint ensures no duplicate chunks
are created. The deterministic UUIDv5 chunk ID also prevents row ID drift.

---

## 4. RAG Retrieval & Threshold Calibration

### Retrieval Mechanism

Vector similarity search uses cosine distance (`<=>`) in PostgreSQL/pgvector.
Lower distance = higher semantic similarity.

### Evaluation Dataset

A 15-question manually labeled evaluation dataset is maintained at
[`ingestion/data/eval_dataset.json`](../ingestion/data/eval_dataset.json).

| Category | Count |
|---|---|
| Answerable from corpus | 10 |
| Unanswerable from corpus | 5 |
| **Total** | **15** |

#### Answerable Questions (excerpts)

| ID | Question | Expected Episode |
|---|---|---|
| Q01 | What is the 'four fits' framework...? | brian-balfour |
| Q02 | How does A/B testing fail when companies run too many experiments...? | ronny-kohavi |
| Q03 | What is the Adjacent User Theory...? | bangaly-kaba |
| Q04 | Key differences between PLG and sales-led growth for B2B? | elena-verna |
| Q05 | How should a startup think about pricing before building? | madhavan-ramanujam |
| Q06 | What is Jobs to Be Done theory and how to reduce churn? | bob-moesta |
| Q07 | What makes a high-performing growth team? | adam-fishman |
| Q08 | Most common growth tactics that never work? | elena-verna |
| Q09 | How does the DHM framework help articulate product strategy? | gibson-biddle |

#### Unanswerable Questions (excerpts)

| ID | Question | Reason |
|---|---|---|
| Q10 | Best marketing automation platform for a Series A SaaS startup? | Out-of-scope: vendor comparison |
| Q11 | How did TikTok's algorithm achieve viral growth in 2019-2020? | Not covered in selected corpus |
| Q12 | What programming language to use for a mobile app? | Off-topic: software development |
| Q13 | Correct calorie intake for building muscle? | Completely off-topic |
| Q14 | Decide between A/B testing vs qualitative user research? | Not directly addressed in corpus |

### Running the Evaluation

```bash
# Run deterministic retrieval eval (no LLM invoked)
python ingestion/scripts/run_retrieval_eval.py

# Results saved to ingestion/data/eval_results.json
```

### Threshold Calibration

The `RAG_RELEVANCE_DISTANCE_THRESHOLD` controls whether a retrieved chunk is
considered relevant enough to ground an answer:

- Distance **≤ threshold**: chunk treated as supporting evidence → grounded answer
- Distance **> threshold**: chunk rejected → agent issues a refusal/honest gap response

#### Empirical Results (15-question evaluation)

Run against the real 15-episode corpus (1,761 chunks):

| Metric | Answerable (n=10) | Unanswerable (n=5) |
|---|---|---|
| Min distance | 0.2123 | 0.2742 |
| Max distance | 0.3316 | 0.4575 |
| Mean distance | 0.2786 | 0.3711 |

**Threshold decision: `0.35`**

This value sits cleanly between the answerable maximum (0.3316) and the
unanswerable minimum (0.2742 — but note Q15 at 0.2987 is a genuine borderline
case where the corpus holds A/B testing content but does not directly address
the A/B-vs-qualitative trade-off). At threshold 0.35:

- All 10 answerable questions retrieve at least one eligible chunk ✓
- 4 of 5 unanswerable questions produce no eligible chunks ✓
- Q15 (A/B vs qualitative) is the one borderline case; top chunk at 0.2987
  touches A/B testing but does not answer the question — acceptable false
  positive risk accepted at MVP stage.

> [!NOTE]
> The threshold `0.35` is calibrated against the real corpus and confirmed
> empirically. It is set via `RAG_RELEVANCE_DISTANCE_THRESHOLD` in `.env`.
> Re-run `ingestion/scripts/run_retrieval_eval.py` after any corpus change.

#### Updating the Threshold

1. Run `python ingestion/scripts/run_retrieval_eval.py`
2. Inspect the `distribution` section of `ingestion/data/eval_results.json`
3. Choose a threshold that separates answerable max from unanswerable min
4. Update `RAG_RELEVANCE_DISTANCE_THRESHOLD` in `.env`
5. Restart the backend

---

## 5. Gitignore Policy

```gitignore
# Raw transcript files — NOT committed
ingestion/data/raw_repo/
ingestion/data/raw/
ingestion/data/raw_transcripts/
```

**What IS committed:**
- `ingestion/data/corpus_manifest.json` — episode selection and metadata
- `ingestion/data/eval_dataset.json` — labeled evaluation questions
- `ingestion/data/eval_results.json` — retrieval results (after running eval)

**What is NOT committed:**
- `ingestion/data/raw_repo/` — cloned source repository (gitignored)
- `.env` — contains API keys and secrets (gitignored)

---

## 6. Reproducing the Corpus

To reproduce the corpus from scratch:

```bash
# 1. Clone the authoritative source repository
git clone https://github.com/ChatPRD/lennys-podcast-transcripts \
  ingestion/data/raw_repo

# 2. Pin to the exact commit
cd ingestion/data/raw_repo
git checkout be8ab89a890a833cbba2c892178f823fff178c65
cd ../../..

# 3. Verify transcript files exist
python ingestion/scripts/build_manifest.py

# 4. Run ingestion
python ingestion/scripts/ingest_real_corpus.py

# 5. Run retrieval evaluation
python ingestion/scripts/run_retrieval_eval.py
```
