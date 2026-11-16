from app.services.document_extraction import extract_document_text
from app.services.document_chunking import chunk_text


def process_document(
    storage_path: str,
    file_type: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> list[str]:

    extracted_text = extract_document_text(
        storage_path=storage_path,
        file_type=file_type
    )

    chunks = chunk_text(
        text=extracted_text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    if not chunks:
        raise ValueError("Document produced no chunks")

    return chunks