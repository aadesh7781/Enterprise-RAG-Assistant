
import requests

from app.core.config import settings


JINA_RERANK_URL = "https://api.jina.ai/v1/rerank"
MODEL_NAME = "jina-reranker-v3.5"
REQUEST_TIMEOUT = 60


def rerank_chunks(
    query: str,
    candidates: list[dict],
    top_k: int = 5
) -> list[dict]:
    """
    Rerank retrieved chunks using Jina AI.
    """

    if not candidates:
        return []

    if not settings.jina_api_key:
        raise RuntimeError("JINA_API_KEY is not configured")

    payload = {
        "model": MODEL_NAME,
        "query": query,
        "documents": [
            chunk["text"] for chunk in candidates
        ],
        "top_n": min(top_k, len(candidates)),
        "return_documents": False,
    }

    headers = {
        "Authorization": f"Bearer {settings.jina_api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            JINA_RERANK_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        detail = ""
        if exc.response is not None:
            detail = exc.response.text[:1000]

        raise RuntimeError(
            f"Jina reranking request failed: {exc}. {detail}"
        ) from exc

    results = response.json().get("results", [])

    reranked_results = []

    for item in results:
        index = item["index"]

        if index < 0 or index >= len(candidates):
            raise RuntimeError("Jina returned an invalid document index")

        result = candidates[index].copy()
        result["rerank_score"] = float(item["relevance_score"])
        reranked_results.append(result)

    return reranked_results
