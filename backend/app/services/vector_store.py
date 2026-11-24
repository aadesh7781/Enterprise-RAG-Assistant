
from pathlib import Path
from uuid import UUID

import chromadb

from app.services.embedding_service import generate_embeddings


PROJECT_ROOT = Path(__file__).resolve().parents[3]

CHROMA_STORAGE_DIR = PROJECT_ROOT / "chroma_db"

# Keep the previous MiniLM collection untouched.
COLLECTION_NAME = "enterprise_documents_jina_v3"


def get_collection():
    CHROMA_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(CHROMA_STORAGE_DIR)
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "hnsw:space": "cosine",
            "embedding_model": "jina-embeddings-v3",
            "embedding_dimensions": 1024
        }
    )

    return collection


def store_document_chunks(
    document_id: UUID,
    chunks: list[str],
    file_type: str
) -> int:

    if not chunks:
        raise ValueError("Cannot store an empty chunk list")

    collection = get_collection()

    embeddings = generate_embeddings(
        chunks,
        task="retrieval.passage"
    )

    document_id_str = str(document_id)

    # Remove old chunks for this document in the Jina collection only.
    collection.delete(
        where={"document_id": document_id_str}
    )

    chunk_ids = [
        f"{document_id_str}_{index}"
        for index in range(len(chunks))
    ]

    metadatas = [
        {
            "document_id": document_id_str,
            "chunk_index": index,
            "file_type": file_type.upper()
        }
        for index in range(len(chunks))
    ]

    collection.upsert(
        ids=chunk_ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return len(chunks)


def delete_document_chunks(document_id: UUID) -> None:
    """
    Delete every vector chunk associated with a document
    from the active Jina collection.
    """

    collection = get_collection()

    collection.delete(
        where={"document_id": str(document_id)}
    )
