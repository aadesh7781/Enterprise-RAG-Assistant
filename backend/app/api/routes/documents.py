
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status
)
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


router = APIRouter(
    prefix="/api/v1/documents",
    tags=["Documents"]
)


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

    user_roles = {role.name for role in current_user.roles}

    # Determine document ownership department.

    if "SUPER_ADMIN" in user_roles:

        if department_id is None:
            raise HTTPException(
                status_code=400,
                detail="Super Admin must provide a department ID"
            )

        target_department_id = department_id

    else:

        if current_user.department_id is None:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to a department"
            )

        if (
            department_id is not None
            and department_id != current_user.department_id
        ):
            raise HTTPException(
                status_code=403,
                detail="You can only upload documents for your department"
            )

        target_department_id = current_user.department_id

    department = db.get(Department, target_department_id)

    if department is None:
        raise HTTPException(
            status_code=404,
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
            status_code=400,
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

        # Grant initial access to the owning department.
        department_grants=[department]
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)

        # Schedule document ingestion after successful DB commit.
        background_tasks.add_task(
            process_document_background,
            str(document.id)
        )

        return document

    except Exception:
        db.rollback()

        delete_stored_file(storage_path)

        raise HTTPException(
            status_code=500,
            detail="Document upload could not be completed"
        )
