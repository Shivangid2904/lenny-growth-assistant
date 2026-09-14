from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from fastapi.responses import StreamingResponse
from app.models.artifact import Artifact
from app.schemas.artifact import ArtifactResponse
from app.schemas.session import (
    SessionCreate,
    SessionResponse,
    SessionDetailResponse,
    MessageCreate,
)
from app.services.session_service import (
    create_session,
    list_sessions,
    get_session,
    delete_session,
)
from app.services.agent_service import process_chat_message

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_new_session(
    session_in: SessionCreate = SessionCreate(),
    db: Session = Depends(get_db),
) -> SessionResponse:
    session = create_session(db, session_in)
    return session


@router.get("", response_model=List[SessionResponse])
def get_all_sessions(
    db: Session = Depends(get_db),
) -> List[SessionResponse]:
    return list_sessions(db)


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session_by_id(
    session_id: UUID,
    db: Session = Depends(get_db),
) -> SessionDetailResponse:
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SESSION_NOT_FOUND",
                "message": f"Session '{session_id}' not found.",
            },
        )
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session_by_id(
    session_id: UUID,
    db: Session = Depends(get_db),
):
    deleted = delete_session(db, session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SESSION_NOT_FOUND",
                "message": f"Session '{session_id}' not found.",
            },
        )
    return None


@router.post("/{session_id}/messages")
async def send_session_message(
    session_id: UUID,
    message_in: MessageCreate,
    db: Session = Depends(get_db),
):
    """Submit a user message and stream the assistant response via Server-Sent Events (SSE)."""
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SESSION_NOT_FOUND",
                "message": f"Session '{session_id}' not found.",
            },
        )

    return StreamingResponse(
        process_chat_message(db=db, session_id=session_id, user_content=message_in.content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{session_id}/artifacts", response_model=List[ArtifactResponse])
def get_session_artifacts(
    session_id: UUID,
    db: Session = Depends(get_db),
) -> List[ArtifactResponse]:
    """Retrieve all artifacts generated for the given session."""
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SESSION_NOT_FOUND",
                "message": f"Session '{session_id}' not found.",
            },
        )
    artifacts = (
        db.query(Artifact)
        .filter(Artifact.session_id == session_id)
        .order_by(Artifact.created_at.asc())
        .all()
    )
    return artifacts


@router.get("/{session_id}/artifacts/{artifact_id}", response_model=ArtifactResponse)
def get_session_artifact(
    session_id: UUID,
    artifact_id: UUID,
    db: Session = Depends(get_db),
) -> ArtifactResponse:
    """Retrieve a specific artifact by ID within a session."""
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SESSION_NOT_FOUND",
                "message": f"Session '{session_id}' not found.",
            },
        )
    artifact = (
        db.query(Artifact)
        .filter(Artifact.session_id == session_id, Artifact.id == artifact_id)
        .first()
    )
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ARTIFACT_NOT_FOUND",
                "message": f"Artifact '{artifact_id}' not found.",
            },
        )
    return artifact


