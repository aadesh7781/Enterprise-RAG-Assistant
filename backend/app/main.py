
from uuid import uuid4

from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.chat import ChatRequest, ChatResponse
from app.database.session import get_db
from app.api.routes.auth import router as auth_router
from app.api.routes.admin import router as admin_router


app = FastAPI(
    title="Enterprise RAG Assistant",
    description="Secure enterprise knowledge assistant API",
    version="1.0.0"
)

# Register authentication routes
app.include_router(auth_router)
app.include_router(admin_router)

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "application": "Enterprise RAG Assistant"
    }


@app.get("/api/v1/health/database")
def database_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "status": "connected",
        "database": "Neon PostgreSQL"
    }


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    conversation_id = request.conversation_id or uuid4()

    return ChatResponse(
        conversation_id=conversation_id,
        answer=f"You asked: {request.question}"
    )


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
