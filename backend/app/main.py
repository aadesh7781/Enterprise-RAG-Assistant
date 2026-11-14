from uuid import uuid4
from fastapi import FastAPI, Depends

from fastapi import FastAPI
from app.schemas.chat import ChatRequest, ChatResponse

app = FastAPI(
    title="Enterprise RAG Assistant",
    description="Secure enterprise knowledge assistant API",
    version="1.0.0"
)


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "application": "Enterprise RAG Assistant"
    }


@app.post(
    "/api/v1/chat",
    response_model=ChatResponse
)
def chat(request: ChatRequest):

    conversation_id = request.conversation_id or uuid4()

    return ChatResponse(
        conversation_id=conversation_id,
        answer=f"You asked: {request.question}"
    )


app = FastAPI()


def get_pagination():
    return {
        "limit": 10,
        "offset": 0
    }


@app.get("/api/v1/documents")
def get_documents(pagination: dict = Depends(get_pagination)):

    return {
        "message": "Documents retrieved",
        "pagination": pagination
    }