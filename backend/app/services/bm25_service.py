
import re

from rank_bm25 import BM25Plus

from app.services.vector_store import get_collection


STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were",
    "what", "who", "when", "where", "why", "how",
    "can", "could", "would", "should", "do", "does",
    "did", "i", "we", "you", "they", "he", "she",
    "it", "my", "our", "your", "their", "this", "that",
    "to", "of", "in", "on", "at", "for", "from",
    "and", "or", "but", "with", "by",
    "company", "policy",
}


def tokenize(text: str) -> list[str]:
    """
    Convert text into lowercase tokens and remove stopwords.
    """
    tokens = re.findall(r"\b\w+\b", text.lower())

    return [
        token for token in tokens
        if token not in STOPWORDS
    ]


def search_bm25(
    query: str,
    authorized_document_ids: list[str],
    top_k: int = 5,
) -> list[dict]:

    if not authorized_document_ids:
        return []

    collection = get_collection()

    if collection.count() == 0:
        return []

    results = collection.get(
        where={
            "document_id": {
                "$in": authorized_document_ids
            }
        },
        include=["documents", "metadatas"],
    )

    documents = results["documents"] or []
    metadatas = results["metadatas"] or []

    if not documents:
        return []

    tokenized_query = tokenize(query)

    if not tokenized_query:
        return []

    valid_documents = []

    for document, metadata in zip(documents, metadatas):
        tokens = tokenize(document)

        if tokens:
            valid_documents.append(
                (tokens, document, metadata)
            )

    if not valid_documents:
        return []

    tokenized_documents = [
        item[0] for item in valid_documents
    ]

    documents = [
        item[1] for item in valid_documents
    ]

    metadatas = [
        item[2] for item in valid_documents
    ]

    bm25 = BM25Plus(tokenized_documents)

    scores = bm25.get_scores(tokenized_query)

    query_terms = set(tokenized_query)

    matching_indices = [
        index
        for index, tokens in enumerate(tokenized_documents)
        if query_terms.intersection(tokens)
    ]

    ranked_indices = sorted(
        matching_indices,
        key=lambda index: scores[index],
        reverse=True,
    )

    retrieved_chunks = []

    for index in ranked_indices[:top_k]:

        metadata = metadatas[index]

        retrieved_chunks.append({
            "document_id": metadata["document_id"],
            "chunk_index": metadata["chunk_index"],
            "file_type": metadata["file_type"],
            "text": documents[index],
            "bm25_score": float(scores[index]),
        })

    return retrieved_chunks
