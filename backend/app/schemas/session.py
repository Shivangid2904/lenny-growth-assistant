from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SessionCreate(BaseModel):
    title: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)

    @field_validator("content")
    @classmethod
    def validate_non_whitespace(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty or whitespace only.")
        return v.strip()

    model_config = ConfigDict(extra="forbid")


class Citation(BaseModel):
    episode_title: str
    guest_name: str
    source_url: str
    chunk_index: int

    model_config = ConfigDict(extra="forbid")


class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_metadata(cls, data: Any) -> Any:
        if hasattr(data, "message_metadata"):
            return {
                "id": data.id,
                "session_id": data.session_id,
                "role": data.role,
                "content": data.content,
                "metadata": data.message_metadata or {},
                "created_at": data.created_at,
            }
        return data


class SessionResponse(BaseModel):
    id: UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionDetailResponse(BaseModel):
    id: UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)

