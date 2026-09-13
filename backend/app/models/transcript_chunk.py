import uuid
from sqlalchemy import Column, String, Integer, Text, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.db.base import Base


class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    episode_id = Column(String(128), nullable=False, index=True)
    episode_title = Column(String(255), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    # "metadata" is reserved on DeclarativeBase, so we name the column "metadata" in SQL
    # while exposing chunk_metadata / property metadata in Python
    chunk_metadata = Column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        default=dict,
    )
    embedding = Column(Vector(768), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    @property
    def metadata_dict(self):
        return self.chunk_metadata

    @metadata_dict.setter
    def metadata_dict(self, val):
        self.chunk_metadata = val
