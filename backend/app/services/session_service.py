from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session as DbSession, joinedload
from app.models.session import Session
from app.schemas.session import SessionCreate


def create_session(db: DbSession, session_in: SessionCreate) -> Session:
    session = Session(title=session_in.title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(db: DbSession) -> List[Session]:
    return db.query(Session).order_by(Session.created_at.desc()).all()


def get_session(db: DbSession, session_id: UUID) -> Optional[Session]:
    return (
        db.query(Session)
        .options(joinedload(Session.messages))
        .filter(Session.id == session_id)
        .first()
    )


def delete_session(db: DbSession, session_id: UUID) -> bool:
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        return False
    db.delete(session)
    db.commit()
    return True
