from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse
from app.services.retrieval_service import search_transcript_chunks
from app.services.embedding_service import OllamaUnavailableError, EmbeddingDimensionMismatchError

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalResponse)
def search_transcripts(
    request: RetrievalRequest,
    db: Session = Depends(get_db),
) -> RetrievalResponse:
    try:
        results = search_transcript_chunks(
            db=db,
            query=request.query,
            top_k=request.top_k,
        )
    except OllamaUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "OLLAMA_UNAVAILABLE",
                "message": str(exc),
            },
        )
    except EmbeddingDimensionMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "EMBEDDING_DIMENSION_MISMATCH",
                "message": str(exc),
            },
        )

    return RetrievalResponse(
        query=request.query,
        count=len(results),
        results=results,
    )
