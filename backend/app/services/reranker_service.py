
from sentence_transformers import CrossEncoder


MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_reranker = None


def get_reranker():
    """
    Load the cross-encoder once and reuse it.
    """

    global _reranker

    if _reranker is None:
        _reranker = CrossEncoder(
            MODEL_NAME,
            device="cpu"
        )

    return _reranker


def rerank_chunks(query, candidates, top_k=5):
    """
    Score query-document pairs and return the
    highest-scoring candidate chunks.
    """

    if not candidates:
        return []

    model = get_reranker()

    pairs = [
        (query, chunk["text"])
        for chunk in candidates
    ]

    scores = model.predict(
        pairs,
        show_progress_bar=False
    )

    reranked_results = []

    for chunk, score in zip(candidates, scores):
        result = chunk.copy()
        result["rerank_score"] = float(score)
        reranked_results.append(result)

    reranked_results.sort(
        key=lambda item: item["rerank_score"],
        reverse=True
    )

    return reranked_results[:top_k]
