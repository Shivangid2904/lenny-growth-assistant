import os
import re
import json
import uuid
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy import text, select, func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.models.transcript_chunk import TranscriptChunk
from app.services.embedding_service import embedding_service, EmbeddingService

logger = logging.getLogger(__name__)


def normalize_transcript(text_content: str) -> str:
    """
    Deterministically clean and normalize transcript text without altering semantic content.
    - Standardizes line endings to \n
    - Normalizes non-breaking spaces and tabs
    - Strips trailing line whitespace
    - Collapses runs of spaces on lines
    - Collapses excessive blank lines (3+ to 2)
    - Strips document-level leading/trailing whitespace
    """
    if not text_content:
        return ""

    # 1. Standardize line endings
    normalized = text_content.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Replace non-breaking spaces and tabs with standard space
    normalized = normalized.replace("\xa0", " ").replace("\t", " ")

    # 3. Process line by line: collapse horizontal whitespace and strip ends
    lines = []
    for line in normalized.split("\n"):
        cleaned_line = re.sub(r" +", " ", line).strip()
        lines.append(cleaned_line)

    normalized = "\n".join(lines)

    # 4. Collapse 3 or more consecutive newlines down to 2
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)

    # 5. Final strip
    return normalized.strip()


def chunk_transcript(
    text_content: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> List[str]:
    """
    Deterministically split normalized transcript text into overlapping chunks.
    - Prefers splitting on paragraph boundaries (\n\n) or sentence boundaries.
    - Prevents empty chunks.
    - Guarantees complete coverage of transcript content.
    """
    if not text_content or not text_content.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be non-negative and strictly less than chunk_size.")

    # Split into paragraphs first
    paragraphs = [p for p in text_content.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text_content.strip()]

    chunks: List[str] = []
    current_chunk: List[str] = []
    current_length = 0

    for paragraph in paragraphs:
        # If single paragraph exceeds chunk_size, split by sentences or hard length
        if len(paragraph) > chunk_size:
            # Flush existing chunk before processing oversized paragraph
            if current_chunk:
                chunk_str = "\n\n".join(current_chunk).strip()
                if chunk_str:
                    chunks.append(chunk_str)
                current_chunk = []
                current_length = 0

            # Split paragraph by sentences or window
            sentences = re.split(r"(?<=[.?!])\s+", paragraph)
            sub_chunk = []
            sub_len = 0
            for s in sentences:
                s_clean = s.strip()
                if not s_clean:
                    continue
                if sub_len + len(s_clean) + 1 > chunk_size and sub_chunk:
                    chunk_text = " ".join(sub_chunk).strip()
                    if chunk_text:
                        chunks.append(chunk_text)
                    # Retain overlap from end of sub_chunk
                    overlap_chars = 0
                    kept = []
                    for item in reversed(sub_chunk):
                        if overlap_chars + len(item) < chunk_overlap:
                            kept.insert(0, item)
                            overlap_chars += len(item)
                        else:
                            break
                    sub_chunk = kept
                    sub_len = sum(len(x) + 1 for x in sub_chunk)

                sub_chunk.append(s_clean)
                sub_len += len(s_clean) + 1

            if sub_chunk:
                chunk_text = " ".join(sub_chunk).strip()
                if chunk_text:
                    chunks.append(chunk_text)
            continue

        # Normal paragraph accumulation
        if current_length + len(paragraph) + 2 > chunk_size and current_chunk:
            chunk_str = "\n\n".join(current_chunk).strip()
            if chunk_str:
                chunks.append(chunk_str)

            # Carry over overlap
            overlap_chars = 0
            kept_paragraphs = []
            for p in reversed(current_chunk):
                if overlap_chars + len(p) < chunk_overlap:
                    kept_paragraphs.insert(0, p)
                    overlap_chars += len(p)
                else:
                    break
            current_chunk = kept_paragraphs
            current_length = sum(len(p) + 2 for p in current_chunk)

        current_chunk.append(paragraph)
        current_length += len(paragraph) + 2

    if current_chunk:
        chunk_str = "\n\n".join(current_chunk).strip()
        if chunk_str:
            chunks.append(chunk_str)

    return chunks


import yaml


def compute_chunk_id(episode_id: str, chunk_index: int) -> uuid.UUID:
    """Generate a deterministic UUIDv5 for idempotency."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"lenny:{episode_id}:{chunk_index}")


def parse_transcript_file(
    file_path: Path,
    override_metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Load transcript metadata and text from JSON or Markdown, supporting YAML frontmatter."""
    override = override_metadata or {}
    if file_path.suffix.lower() == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "episode_id": override.get("episode_id") or data.get("episode_id", file_path.stem),
            "episode_title": override.get("episode_title") or data.get("episode_title", file_path.stem),
            "guest_name": override.get("guest_name") or data.get("guest_name"),
            "source_url": override.get("source_url") or data.get("source_url"),
            "text": data.get("text") or data.get("content") or "",
        }
    elif file_path.suffix.lower() in (".md", ".txt"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        frontmatter = {}
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    body = parts[2]
                except Exception:
                    body = content

        # Determine episode_id: if file is transcript.md, use parent directory name
        if file_path.stem.lower() == "transcript":
            ep_id = file_path.parent.name
        else:
            ep_id = file_path.stem

        # Clean markdown headers from transcript body
        cleaned_body = re.sub(r"^#+\s+.*$", "", body, flags=re.MULTILINE).strip()

        title = (
            override.get("episode_title")
            or frontmatter.get("title")
            or file_path.stem.replace("-", " ").replace("_", " ").title()
        )
        # If title has markdown h1 prefix, clean it
        title = re.sub(r"^#\s+", "", title).strip()

        guest_name = override.get("guest_name") or frontmatter.get("guest")
        source_url = override.get("source_url") or frontmatter.get("youtube_url")

        return {
            "episode_id": override.get("episode_id") or ep_id,
            "episode_title": title,
            "guest_name": guest_name,
            "source_url": source_url,
            "text": cleaned_body,
        }
    return None


def ingest_file(
    file_path: Path,
    db: Session,
    embedder: EmbeddingService = None,
    override_metadata: Optional[Dict[str, Any]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> Dict[str, Any]:
    """Ingest a single transcript file into PostgreSQL/pgvector idempotently."""
    raw_data = parse_transcript_file(file_path, override_metadata=override_metadata)
    if not raw_data:
        return {"file": str(file_path), "status": "skipped", "reason": "unsupported_extension", "chunks": 0}

    raw_text = raw_data.get("text", "")
    if not raw_text or not raw_text.strip():
        logger.warning("empty_transcript_skipped", extra={"file": str(file_path)})
        return {"file": str(file_path), "status": "skipped", "reason": "empty_content", "chunks": 0}


    logger.info("transcript_loaded", extra={"file": str(file_path), "episode_id": raw_data["episode_id"]})

    # 1. Normalize
    normalized = normalize_transcript(raw_text)

    # 2. Chunk
    chunks = chunk_transcript(normalized, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not chunks:
        return {"file": str(file_path), "status": "skipped", "reason": "no_chunks_generated", "chunks": 0}

    logger.info("chunks_created", extra={"episode_id": raw_data["episode_id"], "count": len(chunks)})

    # 3. Embed & Upsert
    service = embedder or embedding_service
    embeddings = service.embed_texts(chunks)
    inserted_count = 0

    for idx, (chunk_content, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_id = compute_chunk_id(raw_data["episode_id"], idx)

        metadata = {
            "guest_name": raw_data.get("guest_name"),
            "source_url": raw_data.get("source_url"),
            "char_length": len(chunk_content),
            "file_source": file_path.name,
        }

        stmt = insert(TranscriptChunk).values(
            id=chunk_id,
            episode_id=raw_data["episode_id"],
            episode_title=raw_data["episode_title"],
            chunk_index=idx,
            content=chunk_content,
            chunk_metadata=metadata,
            embedding=embedding,
        )
        # Idempotent upsert on (episode_id, chunk_index)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_transcript_chunks_episode_chunk",
            set_={
                "content": stmt.excluded.content,
                "episode_title": stmt.excluded.episode_title,
                "metadata": stmt.excluded.metadata,
                "embedding": stmt.excluded.embedding,
            },
        )
        db.execute(stmt)
        inserted_count += 1

    db.commit()
    return {
        "file": str(file_path),
        "episode_id": raw_data["episode_id"],
        "episode_title": raw_data["episode_title"],
        "status": "success",
        "chunks": inserted_count,
    }


def ingest_directory(
    directory_path: Path,
    db: Session,
    embedder: EmbeddingService = None,
    refresh: bool = False,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> Dict[str, Any]:
    """Ingest all transcript files from directory into PostgreSQL/pgvector."""
    start_time = time.perf_counter()
    logger.info("ingestion_started", extra={"dir": str(directory_path), "refresh": refresh})

    if not directory_path.exists() or not directory_path.is_dir():
        raise FileNotFoundError(f"Transcript directory '{directory_path}' not found.")

    if refresh:
        db.execute(text("TRUNCATE TABLE transcript_chunks CASCADE;"))
        db.commit()
        logger.info("ingestion_refresh_truncated", extra={"table": "transcript_chunks"})

    files = sorted(
        [
            p
            for p in directory_path.rglob("*")
            if p.is_file() and p.suffix.lower() in (".json", ".md", ".txt")
        ]
    )

    results = []
    total_chunks = 0
    for f in files:
        res = ingest_file(
            file_path=f,
            db=db,
            embedder=embedder,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        results.append(res)
        total_chunks += res.get("chunks", 0)

    duration_sec = round(time.perf_counter() - start_time, 2)
    logger.info(
        "ingestion_completed",
        extra={
            "files_processed": len(files),
            "total_chunks": total_chunks,
            "duration_sec": duration_sec,
        },
    )

    return {
        "files_processed": len(files),
        "total_chunks": total_chunks,
        "duration_sec": duration_sec,
        "details": results,
    }


def ingest_manifest(
    manifest_path: Path,
    raw_repo_dir: Path,
    db: Session,
    embedder: EmbeddingService = None,
    refresh: bool = False,
    skip_existing: bool = True,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> Dict[str, Any]:
    """Ingest curated episodes specified in corpus_manifest.json into PostgreSQL/pgvector."""
    start_time = time.perf_counter()
    logger.info("manifest_ingestion_started", extra={"manifest": str(manifest_path), "refresh": refresh, "skip_existing": skip_existing})

    if not manifest_path.exists():
        raise FileNotFoundError(f"Corpus manifest '{manifest_path}' not found.")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    episodes = manifest_data.get("episodes", [])
    if not episodes:
        raise ValueError(f"Corpus manifest '{manifest_path}' contains no episodes.")

    if refresh:
        db.execute(text("TRUNCATE TABLE transcript_chunks CASCADE;"))
        db.commit()
        logger.info("ingestion_refresh_truncated", extra={"table": "transcript_chunks"})

    results = []
    total_chunks = 0

    for ep in episodes:
        source_rel = ep.get("source_path")
        file_path = raw_repo_dir / source_rel
        if not file_path.exists():
            logger.warning("episode_file_missing", extra={"file": str(file_path)})
            results.append({
                "episode_id": ep.get("episode_id"),
                "status": "skipped",
                "reason": f"file_not_found: {source_rel}",
                "chunks": 0,
            })
            continue

        ep_id = ep.get("episode_id")
        if not refresh and skip_existing:
            existing_count = db.execute(
                select(func.count(TranscriptChunk.id)).where(TranscriptChunk.episode_id == ep_id)
            ).scalar()
            if existing_count > 0:
                logger.info(
                    "episode_already_ingested_skipped",
                    extra={"episode_id": ep_id, "chunks": existing_count},
                )
                results.append({
                    "episode_id": ep_id,
                    "status": "skipped_already_ingested",
                    "chunks": existing_count,
                })
                total_chunks += existing_count
                continue

        res = ingest_file(
            file_path=file_path,
            db=db,
            embedder=embedder,
            override_metadata={
                "episode_id": ep.get("episode_id"),
                "episode_title": ep.get("episode_title"),
                "guest_name": ep.get("guest_name"),
                "source_url": ep.get("source_url"),
                "primary_topics": ep.get("primary_topics", []),
            },
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        results.append(res)
        total_chunks += res.get("chunks", 0)

    duration_sec = round(time.perf_counter() - start_time, 2)
    logger.info(
        "manifest_ingestion_completed",
        extra={
            "episodes_processed": len(episodes),
            "total_chunks": total_chunks,
            "duration_sec": duration_sec,
        },
    )

    return {
        "files_processed": len(episodes),
        "total_chunks": total_chunks,
        "duration_sec": duration_sec,
        "details": results,
    }

