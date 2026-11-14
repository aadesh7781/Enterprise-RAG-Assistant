from pydantic import BaseModel, Field
from uuid import UUID


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None

    question: str = Field(
        min_length=1,
        max_length=2000
    )


class ChatResponse(BaseModel):
    conversation_id: UUID
    answer: str