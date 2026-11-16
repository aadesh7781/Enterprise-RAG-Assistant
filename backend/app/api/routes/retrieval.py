from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User
from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse
)
from app.security.permissions import require_roles
from app.services.document_authorization import (
    get_authorized_document_ids
)
from app.services.retrieval_service import (
    search_authorized_chunks
)


router = APIRouter(
    prefix="/api/v1/retrieval",
    tags=["Retrieval"]
)


@router.post(
    "/search",
    response_model=RetrievalResponse
)
def search_documents(
    request: RetrievalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "EMPLOYEE",
            "DEPARTMENT_ADMIN",
            "SUPER_ADMIN"
        )
    )
):

    # Step 1: Identify accessible documents.
    authorized_document_ids = get_authorized_document_ids(
        db=db,
        current_user=current_user
    )

    # Step 2: Search only those documents.
    chunks = search_authorized_chunks(
        query=request.query,
        authorized_document_ids=authorized_document_ids,
        top_k=request.top_k
    )

    return RetrievalResponse(
        results=chunks,
        total_results=len(chunks)
    )