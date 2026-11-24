
from app.services.embedding_service import generate_embeddings
from app.services.vector_store import get_collection
from app.services.bm25_service import search_bm25
from app.services.reranker_service import rerank_chunks


MAX_COSINE_DISTANCE = 0.55
RRF_CONSTANT = 60

# MMR balance:
# 0.7 = prioritize relevance
# 0.3 = penalize similarity between selected chunks
MMR_LAMBDA = 0.7


def search_semantic_chunks(query, authorized_document_ids, top_k):
    if not authorized_document_ids:
        return []

    collection = get_collection()

    if collection.count() == 0:
        return []

    query_embedding = generate_embeddings(
        [query],
        task="retrieval.query"
    )[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"document_id": {"$in": authorized_document_ids}},
        include=["documents", "metadatas", "distances"]
    )

    retrieved_chunks = []

    for document, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        if distance > MAX_COSINE_DISTANCE:
            continue

        retrieved_chunks.append({
            "document_id": metadata["document_id"],
            "chunk_index": metadata["chunk_index"],
            "file_type": metadata["file_type"],
            "text": document,
            "distance": float(distance),
            "bm25_score": None
        })

    return retrieved_chunks


def reciprocal_rank_fusion(ranking_lists, top_k):
    fused_results = {}

    for ranking in ranking_lists:
        for rank, chunk in enumerate(ranking, start=1):
            key = (
                chunk["document_id"],
                chunk["chunk_index"]
            )

            if key not in fused_results:
                fused_results[key] = {
                    **chunk,
                    "distance": chunk.get("distance"),
                    "bm25_score": chunk.get("bm25_score"),
                    "rrf_score": 0.0
                }
            else:
                if chunk.get("distance") is not None:
                    fused_results[key]["distance"] = chunk["distance"]

                if chunk.get("bm25_score") is not None:
                    fused_results[key]["bm25_score"] = chunk["bm25_score"]

            fused_results[key]["rrf_score"] += (
                1.0 / (RRF_CONSTANT + rank)
            )

    ranked_results = sorted(
        fused_results.values(),
        key=lambda item: item["rrf_score"],
        reverse=True
    )

    return ranked_results[:top_k]


def apply_mmr(query, candidates, top_k, lambda_mult=MMR_LAMBDA):
    """
    Select relevant and diverse chunks using Maximal Marginal Relevance.
    """

    if not candidates:
        return []

    if not 0 <= lambda_mult <= 1:
        raise ValueError("lambda_mult must be between 0 and 1")

    if len(candidates) <= top_k:
        return candidates

    texts = [chunk["text"] for chunk in candidates]

    # Generate query and passage embeddings using the correct Jina tasks.
    query_embedding = generate_embeddings(
        [query],
        task="retrieval.query"
    )[0]

    document_embeddings = generate_embeddings(
        texts,
        task="retrieval.passage"
    )

    def cosine_similarity(vector_a, vector_b):
        return sum(
            a * b for a, b in zip(vector_a, vector_b)
        )

    selected_indices = []
    remaining_indices = list(range(len(candidates)))

    while remaining_indices and len(selected_indices) < top_k:
        best_index = None
        best_score = float("-inf")

        for candidate_index in remaining_indices:
            relevance = cosine_similarity(
                document_embeddings[candidate_index],
                query_embedding
            )

            if selected_indices:
                redundancy = max(
                    cosine_similarity(
                        document_embeddings[candidate_index],
                        document_embeddings[selected_index]
                    )
                    for selected_index in selected_indices
                )
            else:
                redundancy = 0.0

            mmr_score = (
                lambda_mult * relevance
                - (1 - lambda_mult) * redundancy
            )

            if mmr_score > best_score:
                best_score = mmr_score
                best_index = candidate_index

        selected_indices.append(best_index)
        remaining_indices.remove(best_index)

    return [
        candidates[index]
        for index in selected_indices
    ]


def search_authorized_chunks(query, authorized_document_ids, top_k=5):
    if not authorized_document_ids:
        return []

    # Retrieve a larger candidate pool.
    candidate_k = max(top_k * 4, 20)

    # 1. Semantic retrieval.
    semantic_results = search_semantic_chunks(
        query,
        authorized_document_ids,
        candidate_k
    )

    # 2. BM25 retrieval.
    bm25_results = search_bm25(
        query,
        authorized_document_ids,
        candidate_k
    )

    # 3. Reciprocal Rank Fusion.
    fused_results = reciprocal_rank_fusion(
        [semantic_results, bm25_results],
        candidate_k
    )

    # 4. MMR selects a diverse candidate pool.
    reranking_k = min(
        len(fused_results),
        max(top_k * 2, 10)
    )

    diversified_results = apply_mmr(
        query=query,
        candidates=fused_results,
        top_k=reranking_k
    )

    # 5. Jina reranks the diversified candidates.
    final_results = rerank_chunks(
        query=query,
        candidates=diversified_results,
        top_k=top_k
    )

    return final_results
