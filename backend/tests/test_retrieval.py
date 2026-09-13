from unittest.mock import patch
from app.models.transcript_chunk import TranscriptChunk
from app.services.retrieval_service import search_transcript_chunks


def test_empty_corpus_returns_empty_list(db):
    """When the corpus is empty, retrieval must return an empty list without error."""
    # Ensure database is empty
    results = search_transcript_chunks(db=db, query="Product-market fit in early stage")
    assert results == []


def test_cosine_retrieval_ordering_and_metadata(db):
    """Verify nearest-neighbor distance ordering, metadata preservation, and similarity score."""
    # Orthogonal vectors in 768 dimensions
    vec1 = [1.0] * 384 + [0.0] * 384
    vec2 = [0.0] * 384 + [1.0] * 384

    c1 = TranscriptChunk(
        episode_id="ep-pmf",
        episode_title="Brian Balfour on PMF",
        chunk_index=0,
        content="Product market fit requires market product fit and channel model fit.",
        chunk_metadata={"guest_name": "Brian Balfour", "source_url": "https://example.com/balfour"},
        embedding=vec1,
    )
    c2 = TranscriptChunk(
        episode_id="ep-loops",
        episode_title="Casey Winters on Loops",
        chunk_index=0,
        content="Growth loops replace linear acquisition funnels.",
        chunk_metadata={"guest_name": "Casey Winters", "source_url": "https://example.com/winters"},
        embedding=vec2,
    )
    db.add_all([c1, c2])
    db.commit()

    # Mock query embedding generation to return vec1
    with patch("app.services.retrieval_service.embedding_service.embed_text", return_value=vec1):
        results = search_transcript_chunks(db=db, query="test query", top_k=2)

    assert len(results) == 2
    # Top result should be c1 with distance ~0
    top = results[0]
    assert top["episode_id"] == "ep-pmf"
    assert top["episode_title"] == "Brian Balfour on PMF"
    assert top["guest_name"] == "Brian Balfour"
    assert top["source_url"] == "https://example.com/balfour"
    assert abs(top["distance"]) < 1e-4
    assert top["similarity"] >= 0.999
    assert "metadata" in top

    # Second result should have higher distance
    assert results[1]["distance"] > top["distance"]


def test_retrieval_api_endpoint(client, db):
    """Verify POST /api/retrieval/search contract and response shape."""
    vec = [0.2] * 768
    c = TranscriptChunk(
        episode_id="ep-elena",
        episode_title="Elena Verna on PLG",
        chunk_index=0,
        content="Product led growth is about self-serve acquisition.",
        chunk_metadata={"guest_name": "Elena Verna", "source_url": "https://example.com/elena"},
        embedding=vec,
    )
    db.add(c)
    db.commit()

    with patch("app.services.retrieval_service.embedding_service.embed_text", return_value=vec):
        response = client.post(
            "/api/retrieval/search",
            json={"query": "What is PLG?", "top_k": 3},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "What is PLG?"
    assert data["count"] == 1
    assert len(data["results"]) == 1
    res0 = data["results"][0]
    assert res0["episode_id"] == "ep-elena"
    assert res0["guest_name"] == "Elena Verna"
    assert res0["source_url"] == "https://example.com/elena"
    assert "distance" in res0
    assert "similarity" in res0
    assert "content" in res0


def test_retrieval_api_validation_error(client):
    """Verify passing invalid parameters returns structured VALIDATION_FAILED error."""
    response = client.post(
        "/api/retrieval/search",
        json={"query": "", "top_k": -1},  # Empty query & invalid top_k
    )
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_FAILED"
