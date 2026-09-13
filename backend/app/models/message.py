import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(
        String(32),
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="valid_message_role"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    # "metadata" is reserved on DeclarativeBase, so we name the column "metadata" in SQL
    message_metadata = Column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        default=dict,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    session = relationship("Session", back_populates="messages")

    @property
    def metadata_dict(self) -> dict:
        return self.message_metadata or {}

    @metadata_dict.setter
    def metadata_dict(self, val: dict) -> None:
        self.message_metadata = val

