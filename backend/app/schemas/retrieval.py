from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Semantic search query")
    top_k: int = Field(5, ge=1, le=50, description="Maximum number of chunks to return")

    model_config = ConfigDict(extra="forbid")


class ChunkSearchResult(BaseModel):
    chunk_id: str
    episode_id: str
    episode_title: str
    guest_name: Optional[str] = None
    source_url: Optional[str] = None
    chunk_index: int
    distance: float
    similarity: float
    content: str
    metadata: Dict[str, Any] = {}

    model_config = ConfigDict(extra="forbid")


class RetrievalResponse(BaseModel):
    query: str
    count: int
    results: List[ChunkSearchResult]

    model_config = ConfigDict(extra="forbid")
