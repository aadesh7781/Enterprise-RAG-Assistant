
from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db

from app.api.routes.auth import router as auth_router
from app.api.routes.admin import router as admin_router
from app.api.routes.documents import router as documents_router
from app.api.routes.retrieval import router as retrieval_router
from app.api.routes.chat import router as chat_router


app = FastAPI(
    title="Enterprise RAG Assistant",
    description="Secure enterprise knowledge assistant API",
    version="1.0.0"
)


# Register API routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(documents_router)
app.include_router(retrieval_router)
app.include_router(chat_router)


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
