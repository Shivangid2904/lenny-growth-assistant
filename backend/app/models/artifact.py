import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Artifact(Base):
    __tablename__ = "artifacts"

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
    type = Column(
        String(32),
        CheckConstraint("type IN ('markdown', 'html')", name="valid_artifact_type"),
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    sanitized = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    artifact_metadata = Column(
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

    session = relationship("Session", back_populates="artifacts")

    @property
    def metadata_dict(self):
        return self.artifact_metadata

    @metadata_dict.setter
    def metadata_dict(self, val):
        self.artifact_metadata = val
