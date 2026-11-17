
from uuid import UUID

from sqlalchemy import select

from app.database.connection import SessionLocal
from app.models import Document
from app.services.document_processor import process_document
from app.services.vector_store import store_document_chunks


def process_document_background(document_id: str) -> None:

    document_uuid = UUID(document_id)

    with SessionLocal() as db:

        document = db.scalar(
            select(Document)
            .where(Document.id == document_uuid)
            .with_for_update()
        )

        if document is None:
            return

        try:
            document.status = "PROCESSING"
            db.commit()

            chunks = process_document(
                storage_path=document.storage_path,
                file_type=document.file_type
            )

            store_document_chunks(
                document_id=document.id,
                chunks=chunks,
                file_type=document.file_type
            )

            document.status = "COMPLETED"
            db.commit()

        except Exception:
            db.rollback()

            failed_document = db.get(
                Document,
                document_uuid
            )

            if failed_document is not None:
                failed_document.status = "FAILED"
                db.commit()
