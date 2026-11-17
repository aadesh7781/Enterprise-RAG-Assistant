
import math
import time

from app.database.connection import SessionLocal
from app.models import User

from app.services.document_authorization import (
    get_authorized_document_ids
)

from app.services.embedding_service import generate_embeddings

from app.services.retrieval_service import (
    search_semantic_chunks,
    reciprocal_rank_fusion,
    apply_mmr
)

from app.services.bm25_service import search_bm25
from app.services.reranker_service import (
    get_reranker,
    rerank_chunks
)


TOP_K = 3
CANDIDATE_K = 20

# Document IDs from the actual indexed corpus.
HR_NEW = "82bf32ad-6255-4451-9e49-e75bf70ceb80"
HR_OLD = "ca003db8-bf31-42f3-934b-5fb9e47ff243"
FINANCE = "f6f16b3b-3652-4e68-a79e-d91207cc123a"
ENGINEERING = "0b862f52-d45a-4a38-b4b2-c6ab680110c3"

# Each key is (document_id, chunk_index).
# Grades are manually assigned from the actual chunk contents.
EVALUATION_DATASET = [
    {
        "query": "How many annual paid leave days are employees entitled to?",
        "grades": {
            (HR_NEW, 0): 3,
            (HR_OLD, 0): 3,
            (HR_NEW, 1): 1
        }
    },
    {
        "query": "Can unused annual leave be carried forward?",
        "grades": {
            (HR_NEW, 1): 3,
            (HR_OLD, 0): 3,
            (HR_NEW, 2): 2,
            (HR_NEW, 0): 1
        }
    },
    {
        "query": "Who approves planned employee leave requests?",
        "grades": {
            (HR_NEW, 0): 3,
            (HR_OLD, 0): 2,
            (HR_NEW, 1): 2
        }
    },
    {
        "query": "What receipts and documents are needed for reimbursement?",
        "grades": {
            (FINANCE, 0): 3,
            (FINANCE, 1): 2
        }
    },
    {
        "query": "What is the deadline for submitting reimbursement claims?",
        "grades": {
            (FINANCE, 0): 3
        }
    },
    {
        "query": "How can I replace a damaged company laptop?",
        "grades": {
            (ENGINEERING, 1): 3,
            (ENGINEERING, 0): 2,
            (ENGINEERING, 2): 1
        }
    },
    {
        "query": "How do I request access to development tools and repositories?",
        "grades": {
            (ENGINEERING, 2): 3,
            (ENGINEERING, 1): 2,
            (ENGINEERING, 0): 1
        }
    },
    {
        "query": "How can employees check their annual leave balance?",
        "grades": {
            (HR_NEW, 1): 3,
            (HR_NEW, 2): 2
        }
    },
    {
        "query": "Which business expenses are eligible for reimbursement?",
        "grades": {
            (FINANCE, 0): 3,
            (FINANCE, 1): 2
        }
    },
    {
        "query": "How do employees request a company laptop?",
        "grades": {
            (ENGINEERING, 0): 3,
            (ENGINEERING, 1): 1
        }
    }
]


def chunk_key(chunk):
    return (
        chunk["document_id"],
        chunk["chunk_index"]
    )


def calculate_metrics(results, grades):
    """
    Chunk-level Precision@K, Recall@K, MRR and nDCG@K.

    Relevance grades >= 2 count as relevant for
    binary precision, recall and MRR.
    nDCG uses the full graded relevance scale.
    """

    retrieved = []
    seen = set()

    for chunk in results:
        key = chunk_key(chunk)

        if key not in seen:
            seen.add(key)
            retrieved.append(key)

    top_results = retrieved[:TOP_K]

    relevant_retrieved = [
        key for key in top_results
        if grades.get(key, 0) >= 2
    ]

    total_relevant = sum(
        1 for grade in grades.values()
        if grade >= 2
    )

    precision = len(relevant_retrieved) / TOP_K

    recall = (
        len(relevant_retrieved) / total_relevant
        if total_relevant else 0.0
    )

    reciprocal_rank = 0.0

    for rank, key in enumerate(retrieved, start=1):
        if grades.get(key, 0) >= 2:
            reciprocal_rank = 1.0 / rank
            break

    # Calculate DCG using graded relevance.
    dcg = 0.0

    for rank, key in enumerate(top_results, start=1):
        relevance = grades.get(key, 0)

        dcg += (
            (2 ** relevance - 1)
            / math.log2(rank + 1)
        )

    # Ideal ranking: highest relevance grades first.
    ideal_grades = sorted(
        grades.values(),
        reverse=True
    )[:TOP_K]

    idcg = sum(
        (2 ** relevance - 1) / math.log2(rank + 1)
        for rank, relevance in enumerate(
            ideal_grades,
            start=1
        )
    )

    ndcg = dcg / idcg if idcg else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "mrr": reciprocal_rank,
        "ndcg": ndcg
    }


def main():
    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.email == "superadmin@company.com"
        ).first()

        if user is None:
            print("Super Admin not found.")
            return

        authorized_ids = get_authorized_document_ids(
            db,
            user
        )

        # Warm up models outside measured query latency.
        generate_embeddings(["evaluation warmup"])
        get_reranker()

        method_results = {
            "Semantic": [],
            "BM25": [],
            "Hybrid RRF": [],
            "Hybrid + MMR": [],
            "Hybrid + MMR + Reranker": []
        }

        latency_results = {
            method: []
            for method in method_results
        }

        for case_number, test_case in enumerate(
            EVALUATION_DATASET,
            start=1
        ):
            query = test_case["query"]
            grades = test_case["grades"]

            print(f"\n[{case_number}/{len(EVALUATION_DATASET)}] {query}")

            # Stage 1: Semantic retrieval.
            start = time.perf_counter()

            semantic = search_semantic_chunks(
                query,
                authorized_ids,
                CANDIDATE_K
            )

            semantic_ms = (
                time.perf_counter() - start
            ) * 1000

            # Stage 2: BM25 retrieval.
            start = time.perf_counter()

            bm25 = search_bm25(
                query,
                authorized_ids,
                CANDIDATE_K
            )

            bm25_ms = (
                time.perf_counter() - start
            ) * 1000

            # Stage 3: RRF fusion.
            start = time.perf_counter()

            fused = reciprocal_rank_fusion(
                [semantic, bm25],
                CANDIDATE_K
            )

            rrf_ms = (
                time.perf_counter() - start
            ) * 1000

            hybrid_ms = (
                semantic_ms + bm25_ms + rrf_ms
            )

            # Stage 4: MMR.
            start = time.perf_counter()

            mmr_results = apply_mmr(
                query,
                fused,
                TOP_K
            )

            mmr_extra_ms = (
                time.perf_counter() - start
            ) * 1000

            # Stage 5: MMR + Cross-Encoder.
            reranking_k = min(
                len(fused),
                max(TOP_K * 2, 10)
            )

            start = time.perf_counter()

            diversified = apply_mmr(
                query,
                fused,
                reranking_k
            )

            reranking_mmr_ms = (
                time.perf_counter() - start
            ) * 1000

            start = time.perf_counter()

            reranked = rerank_chunks(
                query,
                diversified,
                TOP_K
            )

            reranker_ms = (
                time.perf_counter() - start
            ) * 1000

            result_sets = {
                "Semantic": semantic[:TOP_K],
                "BM25": bm25[:TOP_K],
                "Hybrid RRF": fused[:TOP_K],
                "Hybrid + MMR": mmr_results,
                "Hybrid + MMR + Reranker": reranked
            }

            query_latencies = {
                "Semantic": semantic_ms,
                "BM25": bm25_ms,
                "Hybrid RRF": hybrid_ms,
                "Hybrid + MMR": hybrid_ms + mmr_extra_ms,
                "Hybrid + MMR + Reranker": (
                    hybrid_ms
                    + reranking_mmr_ms
                    + reranker_ms
                )
            }

            for method, results in result_sets.items():
                metrics = calculate_metrics(
                    results,
                    grades
                )

                method_results[method].append(metrics)
                latency_results[method].append(
                    query_latencies[method]
                )

        print("\n\nPER-QUERY FINAL PIPELINE RESULTS")
        print("=" * 90)

        for index, case in enumerate(EVALUATION_DATASET):
            metrics = method_results[
                "Hybrid + MMR + Reranker"
            ][index]

            print(f"\nQuery: {case['query']}")
            print(
                f"Precision@3: {metrics['precision']:.3f} | "
                f"Recall@3: {metrics['recall']:.3f} | "
                f"MRR: {metrics['mrr']:.3f} | "
                f"nDCG@3: {metrics['ndcg']:.3f}"
            )

        print("\n\nAGGREGATE RETRIEVAL EVALUATION")
        print("=" * 115)

        print(
            f"{'Method':<30}"
            f"{'P@3':>9}"
            f"{'R@3':>9}"
            f"{'MRR':>9}"
            f"{'nDCG@3':>11}"
            f"{'Latency ms':>15}"
        )

        print("-" * 115)

        for method, results in method_results.items():

            count = len(results)

            averages = {
                metric: sum(
                    item[metric] for item in results
                ) / count
                for metric in (
                    "precision",
                    "recall",
                    "mrr",
                    "ndcg"
                )
            }

            average_latency = (
                sum(latency_results[method]) / count
            )

            print(
                f"{method:<30}"
                f"{averages['precision']:>9.3f}"
                f"{averages['recall']:>9.3f}"
                f"{averages['mrr']:>9.3f}"
                f"{averages['ndcg']:>11.3f}"
                f"{average_latency:>15.2f}"
            )

        print("\nEvaluation queries:", len(EVALUATION_DATASET))
        print("Total indexed chunks: 11")
        print("Top K:", TOP_K)

    finally:
        db.close()


if __name__ == "__main__":
    main()
