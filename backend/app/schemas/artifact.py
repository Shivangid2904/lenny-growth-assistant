from typing import Optional, Dict, Any, Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ArtifactBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    type: Literal["markdown", "html"]
    content: str = Field(..., min_length=1)
    css: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ArtifactCreate(ArtifactBase):
    pass


class ArtifactResponse(ArtifactBase):
    id: UUID
    session_id: UUID
    created_at: datetime
    sanitized: bool = True

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_from_orm(cls, data: Any) -> Any:
        if hasattr(data, "artifact_metadata"):
            meta = data.artifact_metadata or {}
            css = meta.get("css")
            return {
                "id": data.id,
                "session_id": data.session_id,
                "type": data.type,
                "title": data.title,
                "content": data.content,
                "css": css,
                "metadata": meta,
                "sanitized": getattr(data, "sanitized", True),
                "created_at": data.created_at,
            }
        return data
