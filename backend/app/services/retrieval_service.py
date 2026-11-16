from app.services.embedding_service import generate_embeddings
from app.services.vector_store import get_collection


def search_authorized_chunks(
    query: str,
    authorized_document_ids: list[str],
    top_k: int = 5
) -> list[dict]:

    if not authorized_document_ids:
        return []

    collection = get_collection()

    if collection.count() == 0:
        return []

    query_embedding = generate_embeddings([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={
            "document_id": {
                "$in": authorized_document_ids
            }
        },
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    retrieved_chunks = []

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):

        retrieved_chunks.append({
            "document_id": metadata["document_id"],
            "chunk_index": metadata["chunk_index"],
            "file_type": metadata["file_type"],
            "text": document,
            "distance": distance
        })

    return retrieved_chunks