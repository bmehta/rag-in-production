"""
Load golden retrieval eval manifest and query cases.
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "eval" / "golden" / "manifest.json"
DEFAULT_GOLDEN = REPO_ROOT / "eval" / "golden" / "retrieval.jsonl"

@dataclass(frozen=True)
class EvalManifest:
    eval_k: int
    top_k: int
    thresholds: dict[str, float]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvalManifest:
        thresholds = data.get("thresholds") or {}
        return cls(
            eval_k=int(data.get("eval_k", 10)),
            top_k=int(data.get("top_k", 20)),
            thresholds={k: float(v) for k, v in thresholds.items()},
        )


@dataclass(frozen=True)
class EvalCase:
    id: str
    query: str
    tags: list[str]
    relevant_chunk_ids: list[str]
    relevant_pages: list[int]
    relevant_text_any: list[str]

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> EvalCase:
        return cls(
            id=str(row["id"]),
            query=str(row["query"]),
            tags=list(row.get("tags") or []),
            relevant_chunk_ids=list(row.get("relevant_chunk_ids") or []),
            relevant_pages=list(row.get("relevant_pages") or []),
            relevant_text_any=list(row.get("relevant_text_any") or []),
        )

    def has_relevance_labels(self) -> bool:
        return bool(
            self.relevant_chunk_ids
            or self.relevant_pages
            or self.relevant_text_any
        )

    def to_metrics_case(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "tags": self.tags,
            "relevant_chunk_ids": self.relevant_chunk_ids,
            "relevant_pages": self.relevant_pages,
            "relevant_text_any": self.relevant_text_any,
        }


def load_manifest(path: Path | str | None = None) -> EvalManifest:
    """Load eval/golden/manifest.json (or the given path)."""
    manifest_path = Path(path) if path else DEFAULT_MANIFEST
    with manifest_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return EvalManifest.from_dict(data)


def load_golden(path: Path | str | None = None) -> list[EvalCase]:
    """
    Load retrieval.jsonl with validation.

    Rows missing id/query or with no relevance fields are skipped with a warning.
    """
    golden_path = Path(path) if path else DEFAULT_GOLDEN
    cases: list[EvalCase] = []

    with golden_path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                warnings.warn(
                    f"{golden_path}:{line_no}: invalid JSON, skipping ({exc})",
                    stacklevel=2,
                )
                continue

            if not row.get("id") or not row.get("query"):
                warnings.warn(
                    f"{golden_path}:{line_no}: missing id or query, skipping",
                    stacklevel=2,
                )
                continue

            case = EvalCase.from_dict(row)
            if not case.has_relevance_labels():
                warnings.warn(
                    f"{golden_path}:{line_no}: no relevance labels on "
                    f"'{case.id}', skipping",
                    stacklevel=2,
                )
                continue

            cases.append(case)

    return cases


def load_eval_dataset(
    manifest_path: Path | str | None = None,
    golden_path: Path | str | None = None,
) -> tuple[EvalManifest, list[EvalCase]]:
    """Load manifest and golden cases together."""
    return load_manifest(manifest_path), load_golden(golden_path)
