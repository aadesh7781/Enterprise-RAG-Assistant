
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    SourceReference
)
from app.security.permissions import require_roles
from app.services.document_authorization import (
    get_authorized_document_ids
)
from app.services.retrieval_service import search_authorized_chunks
from app.services.llm_service import generate_answer


router = APIRouter(tags=["Chat"])


@router.post("/api/v1/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("EMPLOYEE", "DEPARTMENT_ADMIN", "SUPER_ADMIN")
    )
):
    # Step 1: Determine which documents this user can access.
    authorized_document_ids = get_authorized_document_ids(
        db=db,
        current_user=current_user
    )

    # Step 2: Retrieve relevant chunks only from authorized documents.
    retrieved_chunks = search_authorized_chunks(
        query=request.question,
        authorized_document_ids=authorized_document_ids,
        top_k=request.top_k
    )

    # Step 3: Generate an answer using the retrieved context.
    answer = generate_answer(
        question=request.question,
        retrieved_chunks=retrieved_chunks
    )

    # Step 4: Build structured source references.
    sources = [
        SourceReference(
            source_number=index,
            document_id=chunk["document_id"],
            chunk_index=chunk["chunk_index"],
            file_type=chunk["file_type"]
        )
        for index, chunk in enumerate(retrieved_chunks, start=1)
    ]

    # Step 5: Return the answer and its source metadata.
    return ChatResponse(
        conversation_id=request.conversation_id or uuid4(),
        answer=answer,
        sources=sources
    )
