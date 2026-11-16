
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None

    question: str = Field(
        min_length=1,
        max_length=2000
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=10
    )


class SourceReference(BaseModel):
    source_number: int
    document_id: UUID
    chunk_index: int
    file_type: str


class ChatResponse(BaseModel):
    conversation_id: UUID
    answer: str
    sources: list[SourceReference] = Field(default_factory=list)
