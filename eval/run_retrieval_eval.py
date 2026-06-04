"""
Run hybrid retrieval evaluation against the golden set (no LLM).

Usage (from repo root):
  OPENSEARCH_HOST=localhost python -m eval.run_retrieval_eval
  python -m eval.run_retrieval_eval --golden eval/golden/retrieval.jsonl --top-k 20 --k 10 -v
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from eval.dataset import (  # noqa: E402
    DEFAULT_GOLDEN,
    DEFAULT_MANIFEST,
    load_eval_dataset,
)
from eval.metrics import (  # noqa: E402
    aggregate_by_tag,
    check_thresholds,
    mean_metric,
    score_case,
)


def _truncate(text: str, max_len: int = 48) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _build_aggregates(
    cases: list,
    per_case_scores: list[dict],
    k: int,
) -> dict[str, float]:
    return {
        f"recall_at_{k}": mean_metric([s["recall_at_k"] for s in per_case_scores]),
        "mrr": mean_metric([s["mrr"] for s in per_case_scores]),
        f"ndcg_at_{k}": mean_metric([s["ndcg_at_k"] for s in per_case_scores]),
        f"precision_at_{k}": mean_metric(
            [s["precision_at_k"] for s in per_case_scores]
        ),
    }


def _print_results_table(
    cases: list,
    per_case_scores: list[dict],
    k: int,
    verbose: bool,
) -> None:
    id_w = max(4, max((len(c.id) for c in cases), default=2))
    print(f"\n{'id':<{id_w}}  {'hit@K':>5}  {'rank':>4}  {'pass':>4}  query")
    print("-" * (id_w + 40))
    for case, scores in zip(cases, per_case_scores):
        hit = scores["recall_at_k"] >= 1.0
        rank = scores["first_relevant_rank"]
        rank_str = str(rank) if rank is not None else "-"
        row_pass = "yes" if hit else "no"
        print(
            f"{case.id:<{id_w}}  {('yes' if hit else 'no'):>5}  {rank_str:>4}  "
            f"{row_pass:>4}  {_truncate(case.query)}"
        )
        if verbose:
            print(
                f"  recall={scores['recall_at_k']:.2f}  mrr={scores['mrr']:.3f}  "
                f"ndcg={scores['ndcg_at_k']:.3f}  "
                f"precision={scores['precision_at_k']:.3f}"
            )


def _print_summary(
    aggregates: dict[str, float],
    manifest_thresholds: dict[str, float],
    passed: bool,
    failures: list[str],
    cases: list,
    per_case_scores: list[dict],
    k: int,
    verbose: bool,
) -> None:
    print("\nAggregate metrics")
    print("-" * 40)
    for key, value in sorted(aggregates.items()):
        threshold = manifest_thresholds.get(key)
        if threshold is not None:
            status = "ok" if value >= threshold else "FAIL"
            print(f"  {key}: {value:.4f}  (min {threshold:.4f}) [{status}]")
        else:
            print(f"  {key}: {value:.4f}")

    tag_metrics = ("recall_at_k", "mrr", "ndcg_at_k", "precision_at_k")
    metric_cases = [c.to_metrics_case() for c in cases]
    print("\nBreakdown by tag (mean recall@K, mrr, ndcg, precision)")
    print("-" * 40)
    for metric in tag_metrics:
        by_tag = aggregate_by_tag(metric_cases, per_case_scores, metric)
        if not by_tag:
            continue
        print(f"  {metric}:")
        for tag, value in sorted(by_tag.items()):
            print(f"    {tag}: {value:.4f}")

    print()
    if passed:
        print("Result: PASS (all thresholds met)")
    else:
        print("Result: FAIL")
        for msg in failures:
            print(f"  - {msg}")


async def run_eval(
    manifest_path: Path,
    golden_path: Path,
    top_k: int | None,
    eval_k: int | None,
    verbose: bool,
) -> int:
    from app.query import QueryEngine

    manifest, cases = load_eval_dataset(manifest_path, golden_path)
    search_top_k = top_k if top_k is not None else manifest.top_k
    k = eval_k if eval_k is not None else manifest.eval_k

    if not cases:
        print("No eval cases loaded; check golden file.", file=sys.stderr)
        return 1

    engine = QueryEngine()
    per_case_scores: list[dict] = []

    for case in cases:
        retrieved = await engine.retrieve(case.query, top_k=search_top_k)
        scores = score_case(retrieved, case.to_metrics_case(), k)
        per_case_scores.append(scores)

    _print_results_table(cases, per_case_scores, k, verbose)

    aggregates = _build_aggregates(cases, per_case_scores, k)
    passed, failures = check_thresholds(aggregates, manifest.thresholds)
    _print_summary(
        aggregates,
        manifest.thresholds,
        passed,
        failures,
        cases,
        per_case_scores,
        k,
        verbose,
    )

    return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate hybrid retrieval against the golden set."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to manifest.json (default: eval/golden/manifest.json)",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=DEFAULT_GOLDEN,
        help="Path to retrieval.jsonl (default: eval/golden/retrieval.jsonl)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Retrieval depth (default: manifest top_k)",
    )
    parser.add_argument(
        "-k",
        "--k",
        type=int,
        default=None,
        dest="eval_k",
        help="Metrics cutoff K (default: manifest eval_k)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print per-query metric details",
    )
    args = parser.parse_args(argv)

    return asyncio.run(
        run_eval(
            args.manifest,
            args.golden,
            args.top_k,
            args.eval_k,
            args.verbose,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
