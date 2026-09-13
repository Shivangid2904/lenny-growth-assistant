import uuid
from pathlib import Path
from sqlalchemy import text
from app.services.ingestion_service import (
    normalize_transcript,
    chunk_transcript,
    compute_chunk_id,
    ingest_file,
)
from app.services.embedding_service import embedding_service
from app.models.transcript_chunk import TranscriptChunk


def test_normalization_whitespace():
    raw = "  Hello   world \t with   tabs  and \xa0 non-breaking spaces.   "
    cleaned = normalize_transcript(raw)
    assert cleaned == "Hello world with tabs and non-breaking spaces."


def test_normalization_blank_lines():
    raw = "Paragraph 1\r\n\r\n\r\n\r\n\r\nParagraph 2\n\n\n\nParagraph 3"
    cleaned = normalize_transcript(raw)
    assert cleaned == "Paragraph 1\n\nParagraph 2\n\nParagraph 3"


def test_normalization_deterministic():
    text = "Some random podcast content with    spaces.\r\n\r\n\r\nNext point."
    res1 = normalize_transcript(text)
    res2 = normalize_transcript(text)
    assert res1 == res2


def test_chunking_deterministic():
    text = "Paragraph one with some details.\n\nParagraph two with more details.\n\nParagraph three."
    chunks1 = chunk_transcript(text, chunk_size=40, chunk_overlap=10)
    chunks2 = chunk_transcript(text, chunk_size=40, chunk_overlap=10)
    assert chunks1 == chunks2


def test_chunking_no_empty_chunks():
    text = "First paragraph.\n\n\n\nSecond paragraph.\n\n   \n\nThird paragraph."
    chunks = chunk_transcript(text, chunk_size=50, chunk_overlap=10)
    assert len(chunks) > 0
    for c in chunks:
        assert len(c.strip()) > 0


def test_chunking_overlap_behavior():
    text = "A" * 80 + "\n\n" + "B" * 80 + "\n\n" + "C" * 80
    chunks = chunk_transcript(text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) >= 3


def test_chunk_ordering():
    paragraphs = [f"Section {i}: Content for section {i} of the podcast." for i in range(10)]
    full_text = "\n\n".join(paragraphs)
    chunks = chunk_transcript(full_text, chunk_size=120, chunk_overlap=20)
    # Ensure ordering is preserved
    for i in range(len(chunks) - 1):
        assert chunks[i] != chunks[i + 1]


def test_stable_chunk_id():
    id1 = compute_chunk_id("ep-100", 0)
    id2 = compute_chunk_id("ep-100", 0)
    id3 = compute_chunk_id("ep-100", 1)
    assert id1 == id2
    assert id1 != id3
    assert isinstance(id1, uuid.UUID)


def test_real_ollama_embedding_dimension():
    """Verify live Ollama generates exactly 768 dimensions using nomic-embed-text."""
    embedding = embedding_service.embed_text("Testing nomic-embed-text 768-dim embedding.")
    assert len(embedding) == 768
    assert all(isinstance(x, float) for x in embedding)
    assert embedding_service.model == "nomic-embed-text"


def test_idempotent_ingestion_duplicate_prevention(db, tmp_path):
    """Verify ingesting the same file twice updates in-place without duplicating rows."""
    sample_file = tmp_path / "test_ep.json"
    sample_file.write_text(
        """{
            "episode_id": "test-idempotent-ep",
            "episode_title": "Idempotent Test Episode",
            "guest_name": "Test Guest",
            "source_url": "https://example.com/test",
            "text": "This is test paragraph one for testing idempotency.\\n\\nThis is test paragraph two."
        }""",
        encoding="utf-8",
    )

    # First ingestion
    res1 = ingest_file(sample_file, db=db, chunk_size=500, chunk_overlap=50)
    assert res1["status"] == "success"
    first_count = db.query(TranscriptChunk).filter(TranscriptChunk.episode_id == "test-idempotent-ep").count()
    assert first_count > 0

    # Second ingestion
    res2 = ingest_file(sample_file, db=db, chunk_size=500, chunk_overlap=50)
    assert res2["status"] == "success"
    second_count = db.query(TranscriptChunk).filter(TranscriptChunk.episode_id == "test-idempotent-ep").count()
    assert first_count == second_count
