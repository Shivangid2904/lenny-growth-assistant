import logging
import time
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.transcript_chunk import TranscriptChunk
from app.services.embedding_service import embedding_service, EmbeddingService

logger = logging.getLogger(__name__)


def search_transcript_chunks(
    db: Session,
    query: str,
    top_k: int = 5,
    embedder: EmbeddingService = None,
) -> List[Dict[str, Any]]:
    """
    Perform nearest-neighbor semantic search over transcript chunks using cosine distance (<=>).

    IMPORTANT RETRIEVAL RELEVANCE BOUNDARY:
    This function retrieves the nearest neighbors from pgvector regardless of whether they
    are semantically sufficient to answer the user's question.
    - If the corpus is empty, it returns an empty list [].
    - If the corpus is non-empty, it returns the top-k nearest chunks with their distances.
    The future Agent layer applies a similarity/relevance threshold to decide whether to
    synthesize a grounded answer or refuse due to insufficient evidence.
    """
    if not query or not query.strip():
        return []

    start_time = time.perf_counter()
    logger.info("retrieval_started", extra={"query": query, "top_k": top_k})

    # Check if corpus is empty
    total_chunks = db.query(TranscriptChunk.id).limit(1).count()
    if total_chunks == 0:
        logger.info("retrieval_completed", extra={"results_count": 0, "duration_ms": 0.0, "reason": "empty_corpus"})
        return []

    # 1. Generate query embedding (768-dim) via Ollama
    service = embedder or embedding_service
    query_vector = service.embed_text(query)
    query_vector_str = "[" + ",".join(str(x) for x in query_vector) + "]"

    # 2. Query PostgreSQL pgvector with cosine distance operator <=>
    sql = text(
        """
        SELECT 
            id,
            episode_id,
            episode_title,
            chunk_index,
            content,
            metadata,
            embedding <=> :query_vector AS distance
        FROM transcript_chunks
        ORDER BY embedding <=> :query_vector ASC
        LIMIT :top_k;
        """
    )

    rows = db.execute(sql, {"query_vector": query_vector_str, "top_k": top_k}).fetchall()
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    results = []
    for r in rows:
        meta = r[5] or {}
        dist = float(r[6])
        similarity = round(max(0.0, 1.0 - dist), 4)
        results.append(
            {
                "chunk_id": str(r[0]),
                "episode_id": r[1],
                "episode_title": r[2],
                "guest_name": meta.get("guest_name"),
                "source_url": meta.get("source_url"),
                "chunk_index": r[3],
                "distance": round(dist, 4),
                "similarity": similarity,
                "content": r[4],
                "metadata": meta,
            }
        )

    top_distance = results[0]["distance"] if results else None
    logger.info(
        "retrieval_completed",
        extra={
            "results_count": len(results),
            "top_k": top_k,
            "top_distance": top_distance,
            "duration_ms": duration_ms,
        },
    )

    return results
