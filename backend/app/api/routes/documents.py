
import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User, Department, Document
from app.schemas.document import DocumentResponse
from app.security.permissions import require_roles

from app.services.document_storage import (
    save_upload_file,
    delete_stored_file
)

from app.services.document_ingestion import (
    process_document_background
)

from app.services.document_authorization import (
    get_authorized_document_ids
)

from app.services.vector_store import (
    delete_document_chunks
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/documents",
    tags=["Documents"]
)


# -------------------------
# LIST AUTHORIZED DOCUMENTS
# -------------------------

@router.get(
    "",
    response_model=list[DocumentResponse]
)
def list_documents(
    department_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "EMPLOYEE",
            "DEPARTMENT_ADMIN",
            "SUPER_ADMIN"
        )
    )
):

    user_roles = {
        role.name for role in current_user.roles
    }

    is_super_admin = "SUPER_ADMIN" in user_roles
    is_department_admin = "DEPARTMENT_ADMIN" in user_roles

    statement = select(Document)

    if is_super_admin:
        if department_id is not None:
            statement = statement.where(
                Document.department_id == department_id
            )

    else:
        authorized_ids = get_authorized_document_ids(
            db=db,
            current_user=current_user
        )

        if not authorized_ids:
            return []

        statement = statement.where(
            Document.id.in_([
                UUID(document_id)
                for document_id in authorized_ids
            ])
        )

        if is_department_admin:

            if current_user.department_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not assigned to a department"
                )

            statement = statement.where(
                Document.department_id == current_user.department_id
            )

        if department_id is not None:

            if department_id != current_user.department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You cannot view documents from this department"
                )

            statement = statement.where(
                Document.department_id == department_id
            )

    statement = statement.order_by(
        Document.created_at.desc()
    )

    return db.scalars(statement).all()


# -------------------------
# UPLOAD DOCUMENT
# -------------------------

@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    department_id: UUID | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("DEPARTMENT_ADMIN", "SUPER_ADMIN")
    )
):

    user_roles = {
        role.name for role in current_user.roles
    }

    # Determine document ownership department.

    if "SUPER_ADMIN" in user_roles:

        if department_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Super Admin must provide a department ID"
            )

        target_department_id = department_id

    else:

        if current_user.department_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to a department"
            )

        if (
            department_id is not None
            and department_id != current_user.department_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only upload documents for your department"
            )

        target_department_id = current_user.department_id

    department = db.get(
        Department,
        target_department_id
    )

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    # Save and validate the original file.

    try:
        (
            original_filename,
            stored_filename,
            storage_path,
            file_size
        ) = await save_upload_file(file)

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )

    finally:
        await file.close()

    # Create document metadata.

    document = Document(
        filename=original_filename,
        stored_filename=stored_filename,
        file_type=stored_filename.rsplit(".", 1)[-1].upper(),
        file_size=file_size,
        storage_path=storage_path,
        status="PENDING",
        uploaded_by=current_user.id,
        department_id=department.id,
        department_grants=[department]
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)

        background_tasks.add_task(
            process_document_background,
            str(document.id)
        )

        return document

    except Exception:
        db.rollback()

        delete_stored_file(storage_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload could not be completed"
        )


# -------------------------
# DELETE DOCUMENT
# -------------------------

@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("DEPARTMENT_ADMIN", "SUPER_ADMIN")
    )
):

    user_roles = {
        role.name for role in current_user.roles
    }

    is_super_admin = "SUPER_ADMIN" in user_roles

    # Lock the document row while checking its status and deleting it.
    document = db.scalar(
        select(Document)
        .where(Document.id == document_id)
        .with_for_update()
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Department Admins can only delete their own department's documents.
    if not is_super_admin:

        if current_user.department_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to a department"
            )

        if document.department_id != current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

    # Do not delete while background ingestion is running.
    if document.status == "PROCESSING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is currently being processed. Try again later."
        )

    storage_path = document.storage_path

    try:
        db.delete(document)
        db.commit()

    except Exception:
        db.rollback()

        logger.exception(
            "Database deletion failed for document %s",
            document_id
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document could not be deleted"
        )

    # Database deletion has succeeded. Clean up external storage.
    try:
        delete_document_chunks(document_id)

    except Exception:
        logger.exception(
            "ChromaDB cleanup failed for document %s",
            document_id
        )

    try:
        delete_stored_file(storage_path)

    except Exception:
        logger.exception(
            "Stored file cleanup failed for document %s",
            document_id
        )

    return None
