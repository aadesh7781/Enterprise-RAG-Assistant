
from pydantic import BaseModel, Field


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


class RetrievedChunk(BaseModel):
    document_id: str
    chunk_index: int
    file_type: str
    text: str
    distance: float | None = None
    bm25_score: float | None = None
    rrf_score: float
    rerank_score: float | None = None


class RetrievalResponse(BaseModel):
    results: list[RetrievedChunk]
    total_results: int
