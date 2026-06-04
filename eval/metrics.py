"""
Pure retrieval metrics for hybrid search evaluation.

All functions are side-effect free (no I/O).
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


def is_chunk_relevant(chunk: Mapping[str, Any], case: Mapping[str, Any]) -> bool:
    """
    Return True if a retrieved chunk matches any relevance rule on the case.

    Rules (any match counts):
      - relevant_chunk_ids: exact chunk_id
      - relevant_pages: page_number in list
      - relevant_text_any: case-insensitive substring in text
    """
    chunk_id = chunk.get("chunk_id")
    page_number = chunk.get("page_number")
    text = (chunk.get("text") or "").lower()

    chunk_ids = case.get("relevant_chunk_ids") or []
    if chunk_ids and chunk_id in chunk_ids:
        return True

    pages = case.get("relevant_pages") or []
    if pages and page_number in pages:
        return True

    needles = case.get("relevant_text_any") or []
    if needles:
        for needle in needles:
            if needle.lower() in text:
                return True

    return False


def relevance_flags(
    retrieved: Sequence[Mapping[str, Any]], case: Mapping[str, Any]
) -> list[bool]:
    """Binary relevance label per retrieved chunk, in rank order."""
    return [is_chunk_relevant(chunk, case) for chunk in retrieved]


def first_relevant_rank(
    retrieved: Sequence[Mapping[str, Any]], case: Mapping[str, Any]
) -> int | None:
    """1-based rank of the first relevant chunk, or None if none found."""
    for i, chunk in enumerate(retrieved):
        if is_chunk_relevant(chunk, case):
            return i + 1
    return None


def recall_at_k(
    retrieved: Sequence[Mapping[str, Any]], case: Mapping[str, Any], k: int
) -> float:
    """1.0 if any relevant chunk appears in the top-K results, else 0.0."""
    top = retrieved[:k]
    return 1.0 if any(is_chunk_relevant(chunk, case) for chunk in top) else 0.0


def mrr(
    retrieved: Sequence[Mapping[str, Any]], case: Mapping[str, Any]
) -> float:
    """Mean reciprocal rank: 1 / rank of first relevant hit, or 0 if none."""
    rank = first_relevant_rank(retrieved, case)
    return 0.0 if rank is None else 1.0 / rank


def precision_at_k(
    retrieved: Sequence[Mapping[str, Any]], case: Mapping[str, Any], k: int
) -> float:
    """Fraction of top-K chunks that are relevant."""
    if k <= 0:
        return 0.0
    top = retrieved[:k]
    if not top:
        return 0.0
    relevant_count = sum(1 for chunk in top if is_chunk_relevant(chunk, case))
    return relevant_count / k


def _dcg_at_k(relevances: Sequence[int], k: int) -> float:
    dcg = 0.0
    for i, rel in enumerate(relevances[:k]):
        if rel:
            dcg += 1.0 / math.log2(i + 2)
    return dcg


def ndcg_at_k(
    retrieved: Sequence[Mapping[str, Any]], case: Mapping[str, Any], k: int
) -> float:
    """NDCG@K with binary relevance (standard DCG / IDCG)."""
    if k <= 0:
        return 0.0
    relevances = [1 if is_chunk_relevant(chunk, case) else 0 for chunk in retrieved]
    dcg = _dcg_at_k(relevances, k)
    ideal = sorted(relevances, reverse=True)
    idcg = _dcg_at_k(ideal, k)
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def score_case(
    retrieved: Sequence[Mapping[str, Any]], case: Mapping[str, Any], k: int
) -> dict[str, float | int | None]:
    """Per-query metric bundle for a single golden case."""
    return {
        "recall_at_k": recall_at_k(retrieved, case, k),
        "mrr": mrr(retrieved, case),
        "ndcg_at_k": ndcg_at_k(retrieved, case, k),
        "precision_at_k": precision_at_k(retrieved, case, k),
        "first_relevant_rank": first_relevant_rank(retrieved, case),
    }


def mean_metric(values: Sequence[float]) -> float:
    """Arithmetic mean; returns 0.0 for an empty sequence."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def aggregate_by_tag(
    cases: Sequence[Mapping[str, Any]],
    per_case_scores: Sequence[Mapping[str, float]],
    metric: str,
) -> dict[str, float]:
    """
    Mean of a metric grouped by each tag on the case.

    Cases with multiple tags contribute to each tag bucket.
    """
    buckets: dict[str, list[float]] = {}
    for case, scores in zip(cases, per_case_scores):
        tags = case.get("tags") or ["untagged"]
        value = float(scores[metric])
        for tag in tags:
            buckets.setdefault(tag, []).append(value)
    return {tag: mean_metric(vals) for tag, vals in buckets.items()}


def check_thresholds(
    aggregates: Mapping[str, float], thresholds: Mapping[str, float]
) -> tuple[bool, list[str]]:
    """
    Compare aggregate metrics to manifest thresholds.

    Threshold keys use the same names as aggregate keys (e.g. recall_at_10).
    Returns (passed, list of failure messages).
    """
    failures: list[str] = []
    for key, minimum in thresholds.items():
        actual = aggregates.get(key)
        if actual is None:
            failures.append(f"{key}: missing from aggregates")
            continue
        if actual < minimum:
            failures.append(f"{key}: {actual:.4f} < {minimum:.4f}")
    return len(failures) == 0, failures
