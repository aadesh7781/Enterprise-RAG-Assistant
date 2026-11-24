
import math
import requests

from app.core.config import settings


JINA_EMBEDDINGS_URL = "https://api.jina.ai/v1/embeddings"
MODEL_NAME = "jina-embeddings-v3"
EMBEDDING_DIMENSIONS = 1024
BATCH_SIZE = 64
REQUEST_TIMEOUT = 60


def generate_embeddings(
    texts: list[str],
    task: str = "retrieval.passage"
) -> list[list[float]]:
    """
    Generate normalized embeddings using Jina AI.

    Use retrieval.passage for document chunks and
    retrieval.query for user queries.
    """

    if not texts:
        return []

    if not settings.jina_api_key:
        raise RuntimeError("JINA_API_KEY is not configured")

    if task not in {"retrieval.query", "retrieval.passage"}:
        raise ValueError(f"Unsupported Jina embedding task: {task}")

    headers = {
        "Authorization": f"Bearer {settings.jina_api_key}",
        "Content-Type": "application/json",
    }

    all_embeddings = []

    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]

        payload = {
            "model": MODEL_NAME,
            "task": task,
            "dimensions": EMBEDDING_DIMENSIONS,
            "input": batch,
        }

        try:
            response = requests.post(
                JINA_EMBEDDINGS_URL,
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
                f"Jina embedding request failed: {exc}. {detail}"
            ) from exc

        data = response.json().get("data", [])

        if len(data) != len(batch):
            raise RuntimeError(
                "Jina returned an unexpected number of embeddings"
            )

        # Preserve the original input order.
        data.sort(key=lambda item: item["index"])

        for item in data:
            embedding = item["embedding"]

            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise RuntimeError(
                    f"Expected {EMBEDDING_DIMENSIONS} dimensions, "
                    f"received {len(embedding)}"
                )

            # Normalize vectors for cosine similarity and MMR.
            magnitude = math.sqrt(
                sum(value * value for value in embedding)
            )

            if magnitude == 0:
                raise RuntimeError("Jina returned a zero-length embedding")

            normalized = [
                value / magnitude for value in embedding
            ]

            all_embeddings.append(normalized)

    return all_embeddings
