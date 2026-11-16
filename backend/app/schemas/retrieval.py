from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)

    model_config = ConfigDict(extra="forbid")


class RetrievedChunk(BaseModel):
    document_id: UUID
    chunk_index: int
    file_type: str
    text: str
    distance: float


class RetrievalResponse(BaseModel):
    results: list[RetrievedChunk]
    total_results: int