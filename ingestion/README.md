# Transcript Ingestion & RAG Foundation

This module implements the deterministic ingestion, normalization, chunking, embedding generation, vector storage, and semantic retrieval pipeline for the **Lenny Growth Assistant**.

---

## 1. Overview & Architecture

The ingestion pipeline converts podcast transcripts into 768-dimensional vector representations stored in PostgreSQL using the `pgvector` extension:

```text
Transcript Files (.json / .md)
            ↓
Normalization (deterministic whitespace & format cleanup)
            ↓
Chunking (~1,000 chars / ~200-250 words, 150-char overlap)
            ↓
Ollama nomic-embed-text (local 768-dimensional embeddings)
            ↓
PostgreSQL pgvector (transcript_chunks table with unique constraint)
            ↓
Cosine Distance Retrieval (ORDER BY embedding <=> query_vector)
            ↓
Top-k Nearest Neighbor Chunks + Episode Citations
```

---

## 2. Directory Structure

```text
ingestion/
├── README.md                       # This documentation
├── data/
│   ├── corpus_manifest.json        # Episode selection manifest (committed)
│   ├── eval_dataset.json           # Labeled retrieval evaluation set (committed)
│   ├── eval_results.json           # Retrieval eval output (committed after eval run)
│   ├── raw_repo/                   # Cloned source repo — NOT committed (gitignored)
│   │   └── episodes/
│   │       ├── brian-balfour/transcript.md
│   │       └── ...
│   └── transcripts/                # Legacy fixture files
│       ├── fixture_brian_balfour_retention.json
│       ├── fixture_casey_winters_loops.json
│       └── fixture_elena_verna_plg.json
└── scripts/
    ├── build_manifest.py           # Generates corpus_manifest.json from raw_repo
    ├── ingest.py                   # Legacy standalone ingestion script
    ├── ingest_real_corpus.py       # Real corpus ingestion (uses manifest)
    ├── run_retrieval_eval.py       # Deterministic retrieval evaluation
    ├── select_corpus.py            # Episode selection exploration script
    └── verify_checkpoint4.py      # End-to-end Checkpoint 4 verification
```

### Authoritative Transcript Source

Raw transcripts come from:
- **Repository**: https://github.com/ChatPRD/lennys-podcast-transcripts
- **Pinned commit**: `be8ab89a890a833cbba2c892178f823fff178c65`
- **Clone path**: `ingestion/data/raw_repo/` (gitignored — not committed)
- **Episode selection**: 15 episodes documented in `ingestion/data/corpus_manifest.json`

> **Git policy**: Raw transcript files are never committed to this repository.
> Only the manifest, evaluation dataset, and evaluation results are tracked.

---

## 3. Transcript Input Formats

The pipeline supports both **JSON** and **Markdown/Plain Text** files located in `ingestion/data/transcripts/`.

### Preferred JSON Format
```json
{
  "episode_id": "ep-101",
  "episode_title": "Elena Verna on Product-Led Growth and Product-Led Sales",
  "guest_name": "Elena Verna",
  "source_url": "https://www.lennyspodcast.com/elena-verna-on-plg",
  "text": "Full transcript content goes here..."
}
```

### Markdown / Text Format
Markdown files with optional top-level `# Episode Title` heading:
```markdown
# Elena Verna on Product-Led Growth

Full transcript text...
```

---

## 4. Normalization Strategy

Normalization in [`app.services.ingestion_service.normalize_transcript`](file:///c:/Users/SHIVANGI/OneDrive/Documents/Desktop/Projects/lenny-growth-assistant/backend/app/services/ingestion_service.py) is strictly deterministic and preserves full semantic fidelity:
1. Standardizes all line endings (`\r\n` and `\r` to `\n`).
2. Converts non-breaking spaces (`\xa0`) and tab characters to standard spaces.
3. Collapses runs of horizontal spaces on each line to a single space.
4. Strips leading and trailing line whitespace.
5. Collapses excessive consecutive newlines (3 or more down to 2).
6. Strips leading and trailing document whitespace.

No spoken content is summarized, rewritten, or elided during normalization.

---

## 5. Chunking Strategy

Implemented in [`app.services.ingestion_service.chunk_transcript`](file:///c:/Users/SHIVANGI/OneDrive/Documents/Desktop/Projects/lenny-growth-assistant/backend/app/services/ingestion_service.py):
- **Default Chunk Size:** 1,000 characters (~200–250 words / ~800–1,200 tokens depending on tokenizer).
- **Default Overlap:** 150 characters (~30–40 words).
- **Boundary Preference:** Splits on paragraph breaks (`\n\n`) and sentence endings (`[.?!]`) to keep conceptual thoughts intact.
- **Ordering & Filtering:** Preserves sequential `chunk_index` (0, 1, 2...); empty or whitespace-only chunks are strictly discarded.

### Stored Chunk Metadata
Each chunk stores rich metadata in PostgreSQL `JSONB`:
```json
{
  "guest_name": "Elena Verna",
  "source_url": "https://www.lennyspodcast.com/elena-verna-on-plg",
  "char_length": 836,
  "file_source": "fixture_elena_verna_plg.json"
}
```

---

## 6. Embeddings via Ollama (`nomic-embed-text`)

- **Model:** `nomic-embed-text`
- **Output Dimension:** Exactly `768` dimensions.
- **Provider:** Host-managed Ollama service (`http://localhost:11434` or `http://host.docker.internal:11434`).
- **Invariant:** Regardless of whether the chat reasoning provider is Anthropic Claude or local Ollama, all embeddings (ingestion and retrieval) are generated locally using `nomic-embed-text`.
- **Validation:** The service validates that every returned embedding has length `768`. Disconnections raise `OllamaUnavailableError`, and dimension deviations raise `EmbeddingDimensionMismatchError`. Fake embeddings are never silently generated.

---

## 7. Database Idempotency & Refresh Behavior

### Storage Target
Chunks are stored in the existing `transcript_chunks` table:
```sql
CREATE TABLE transcript_chunks (
    id UUID PRIMARY KEY,
    episode_id VARCHAR(128) NOT NULL,
    episode_title VARCHAR(255) NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_transcript_chunks_episode_chunk UNIQUE (episode_id, chunk_index)
);
```

### Idempotency
- **Stable UUIDv5:** Each chunk ID is deterministically generated using `uuid.uuid5(uuid.NAMESPACE_DNS, f"lenny:{episode_id}:{chunk_index}")`.
- **PostgreSQL Upsert:** Ingestion executes `INSERT ... ON CONFLICT (episode_id, chunk_index) DO UPDATE ...`. Running ingestion multiple times on the same transcript files updates existing rows in place without creating duplicates.

### Refresh Path
To perform a complete clean rebuild of the knowledge base:
```powershell
python ingestion/scripts/ingest.py --refresh
```
The `--refresh` flag executes `TRUNCATE TABLE transcript_chunks CASCADE;` prior to re-chunking and re-embedding.

---

## 8. Ingestion CLI Usage

### Standard Idempotent Ingestion
```powershell
# From project root
.\backend\.venv\Scripts\python.exe ingestion/scripts/ingest.py
```

### Full Refresh (Wipe & Re-embed)
```powershell
.\backend\.venv\Scripts\python.exe ingestion/scripts/ingest.py --refresh
```

### Custom Directory or Chunk Parameters
```powershell
.\backend\.venv\Scripts\python.exe ingestion/scripts/ingest.py --data-dir path/to/transcripts --chunk-size 1200 --chunk-overlap 200
```

---

## 9. Retrieval API & Architectural Boundary

### Semantic Search Endpoint
`POST /api/retrieval/search`

#### Request
```json
{
  "query": "How should a startup think about product-market fit?",
  "top_k": 5
}
```

#### Response
```json
{
  "query": "How should a startup think about product-market fit?",
  "count": 1,
  "results": [
    {
      "chunk_id": "a4d8c6b1-3e5f-5a12-89bc-7789aa01bb22",
      "episode_id": "ep-pmf",
      "episode_title": "[TEST FIXTURE] Brian Balfour on Product Market Fit and Retention Curves",
      "guest_name": "Brian Balfour",
      "source_url": "https://www.lennyspodcast.com/brian-balfour-retention-fixture",
      "chunk_index": 0,
      "distance": 0.2637,
      "similarity": 0.7363,
      "content": "Welcome to this test fixture episode with Brian Balfour...",
      "metadata": {
        "guest_name": "Brian Balfour",
        "source_url": "https://www.lennyspodcast.com/brian-balfour-retention-fixture",
        "char_length": 907
      }
    }
  ]
}
```

### CRITICAL: Retrieval Relevance Boundary
> [!IMPORTANT]
> **Nearest-neighbor retrieval is NOT the same thing as answerability.**
>
> The retrieval layer returns the closest chunks in vector space along with cosine distance (`<=>`), even if the query is unrelated to podcast topics.
>
> The retrieval layer does **not** decide whether to refuse or hallucinate:
> - **Empty Corpus:** Returns `[]` (empty list).
> - **Non-Empty Corpus:** Returns the top-k nearest neighbors with their distances.
>
> The **future Agent layer** (Checkpoint 3) owns the relevance threshold policy (e.g. `distance <= 0.30` or `similarity >= 0.70`). If retrieved content falls below the threshold, the Agent layer emits the explicit grounded refusal message: *"I don't have enough grounded information to answer that based on available episodes."*

---

## 10. Ollama Setup & Troubleshooting

### Requirements
1. Install Ollama: [https://ollama.com](https://ollama.com)
2. Pull the embedding model:
   ```bash
   ollama pull nomic-embed-text
   ```
3. Verify model installation:
   ```bash
   ollama list
   # Output should list nomic-embed-text:latest (274 MB)
   ```
4. Verify HTTP reachability:
   ```bash
   curl http://localhost:11434/api/tags
   ```

### Troubleshooting
- **`OLLAMA_UNAVAILABLE` (503):** Ensure Ollama is running (`ollama serve` or background service on port 11434).
- **`EMBEDDING_DIMENSION_MISMATCH` (500):** Verify `OLLAMA_EMBEDDING_MODEL=nomic-embed-text`. Do not use models with dimension other than 768.

---

## 11. TRACKED PRE-SUBMISSION TODO: REAL LENNY DATASET

> [!WARNING]
> ### Pre-Submission Requirement
> The files currently in `ingestion/data/transcripts/` (`fixture_*.json`) are **test fixtures strictly for development, testing, and pipeline verification**. They are explicitly marked with `[TEST FIXTURE]` titles.
>
> **Before final submission and demo recording, you must:**
> 1. Download or export the representative subset (~20–30 episodes) of authentic Lenny's Podcast transcripts.
> 2. Place the real transcript files into `ingestion/data/transcripts/`.
> 3. Run a clean full ingestion:
>    ```powershell
>    .\backend\.venv\Scripts\python.exe ingestion/scripts/ingest.py --refresh
>    ```
> 4. Verify that real episode titles and chunk counts populate PostgreSQL `transcript_chunks`.
> 5. Run the 15-question evaluation benchmark against the real knowledge base.
