"""
Print ranked retrieval results to help label golden eval cases.

Usage (from repo root):
  OPENSEARCH_HOST=localhost python -m eval.label_queries "What is AC-2?"
  python -m eval.label_queries --top-k 20 --file queries.txt
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

SNIPPET_LEN = 120


def _snippet(text: str, max_len: int = SNIPPET_LEN) -> str:
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= max_len:
        return collapsed
    return collapsed[: max_len - 3] + "..."


def _load_queries_from_file(path: Path) -> list[str]:
    queries: list[str] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                queries.append(line)
    return queries


def _print_ranked_results(query: str, results: list[dict], top_k: int) -> None:
    print(f"\nQuery: {query}")
    print(f"Top {min(len(results), top_k)} results")
    print("-" * 72)
    if not results:
        print("  (no results)")
        return

    for rank, chunk in enumerate(results[:top_k], start=1):
        chunk_id = chunk.get("chunk_id", "?")
        page = chunk.get("page_number", "?")
        score = chunk.get("relevance_score")
        score_str = f"{score:.4f}" if isinstance(score, (int, float)) else "-"
        text = _snippet(chunk.get("text") or "")
        print(f"  {rank:2}. chunk_id={chunk_id}  page={page}  score={score_str}")
        print(f"      {text}")
    print("\nPaste into retrieval.jsonl:")
    print('  "relevant_chunk_ids": ["<chunk_id>", ...],')
    print('  "relevant_pages": [<page_number>, ...],')
    print('  "relevant_text_any": ["<substring>", ...],')


async def label_queries(
    queries: list[str],
    top_k: int,
) -> None:
    from app.query import QueryEngine

    if not queries:
        print("No queries provided.", file=sys.stderr)
        return

    engine = QueryEngine()
    for query in queries:
        results = await engine.retrieve(query, top_k=top_k)
        _print_ranked_results(query, results, top_k)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run retrieval and print ranked chunks for golden-set labeling."
    )
    parser.add_argument(
        "queries",
        nargs="*",
        help="Query strings to run (can combine with --file)",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=None,
        help="Text file with one query per line (# comments ignored)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Number of chunks to retrieve and display (default: 20)",
    )
    args = parser.parse_args(argv)

    queries = list(args.queries)
    if args.file:
        if not args.file.is_file():
            print(f"File not found: {args.file}", file=sys.stderr)
            return 1
        queries.extend(_load_queries_from_file(args.file))

    if not queries:
        parser.print_help()
        return 1

    asyncio.run(label_queries(queries, args.top_k))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
