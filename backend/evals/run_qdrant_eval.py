"""KitchenPilot Qdrant RAG focused evaluation.

Bypasses the intent router and agent graph to test RAG retrieval
and answer quality in isolation.

Usage:
    uv run python evals/run_qdrant_eval.py --mode qdrant-retrieval
    uv run python evals/run_qdrant_eval.py --mode qdrant-answer
    uv run python evals/run_qdrant_eval.py --mode qdrant-multiturn
    uv run python evals/run_qdrant_eval.py --mode qdrant-retrieval --compare-local
    uv run python evals/run_qdrant_eval.py --mode qdrant-retrieval --limit 10
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from kitchenpilot.core.config import Settings
from kitchenpilot.rag.qdrant_store import QdrantRecipeStore
from kitchenpilot.rag.service import RAGService
from kitchenpilot.schemas.enums import ChunkType
from kitchenpilot.schemas.recipe import SourceChunk

EVAL_ROOT = Path(__file__).resolve().parent
DATASET_DIR = EVAL_ROOT / "dataset"
RESULTS_DIR = EVAL_ROOT / "results"

CHUNK_TYPE_ALIASES: dict[str, set[str]] = {
    "beginner_tip": {"step"},
    "failure_reason": {"failure"},
    "safety_note": {"safety"},
    "substitution": {"substitution"},
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunConfig:
    mode: str
    top_k: int
    limit: int | None
    compare_local: bool
    output_prefix: str
    dataset: Path | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Qdrant RAG focused benchmark (bypasses intent router).",
    )
    parser.add_argument(
        "--mode",
        choices=["qdrant-retrieval", "qdrant-answer", "qdrant-multiturn"],
        default="qdrant-retrieval",
        help=(
            "qdrant-retrieval: pure vector search, no LLM. "
            "qdrant-answer: retrieval + LLM generation. "
            "qdrant-multiturn: multi-turn retrieval (bypasses agent)."
        ),
    )
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None, help="Limit cases for smoke runs.")
    parser.add_argument(
        "--compare-local",
        action="store_true",
        default=False,
        help="Also run local lexical retrieval and include overlap metrics.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Custom JSONL dataset path (default: evals/dataset/rag_questions.jsonl).",
    )
    parser.add_argument("--output-prefix", default="")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()
    config = RunConfig(
        mode=args.mode,
        top_k=args.top_k,
        limit=args.limit,
        compare_local=args.compare_local,
        output_prefix=args.output_prefix
        or datetime.now().strftime("qdrant_%Y%m%d_%H%M%S"),
        dataset=args.dataset,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    outputs: dict[str, Any] = {
        "config": {
            "mode": config.mode,
            "top_k": config.top_k,
            "limit": config.limit,
            "compare_local": config.compare_local,
        },
        "results": {},
    }

    if config.mode == "qdrant-retrieval":
        rows = run_qdrant_retrieval(config)
        outputs["results"]["qdrant_retrieval"] = summarize(rows, _RETRIEVAL_METRIC_NAMES)
        write_jsonl(RESULTS_DIR / f"{config.output_prefix}_qdrant_retrieval.jsonl", rows)
        if config.compare_local:
            local_rows = run_local_retrieval(config)
            outputs["results"]["local_retrieval"] = summarize(
                local_rows, _RETRIEVAL_METRIC_NAMES
            )
            write_jsonl(
                RESULTS_DIR / f"{config.output_prefix}_local_retrieval.jsonl", local_rows
            )

    elif config.mode == "qdrant-answer":
        rows = run_qdrant_answer(config)
        outputs["results"]["qdrant_answer"] = summarize(rows, _ANSWER_METRIC_NAMES)
        write_jsonl(RESULTS_DIR / f"{config.output_prefix}_qdrant_answer.jsonl", rows)

    elif config.mode == "qdrant-multiturn":
        rows = run_qdrant_multiturn(config)
        outputs["results"]["qdrant_multiturn"] = summarize(
            rows, _MULTITURN_METRIC_NAMES
        )
        write_jsonl(RESULTS_DIR / f"{config.output_prefix}_qdrant_multiturn.jsonl", rows)

    outputs["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    summary_path = RESULTS_DIR / f"{config.output_prefix}_summary.json"
    write_json(summary_path, outputs)
    print_summary(summary_path, outputs)


# ---------------------------------------------------------------------------
# Run modes
# ---------------------------------------------------------------------------


def run_qdrant_retrieval(config: RunConfig) -> list[dict[str, Any]]:
    """Pure Qdrant vector retrieval – no LLM, no intent router."""
    settings = Settings(rag_use_qdrant=True)
    qdrant_store = QdrantRecipeStore(settings=settings)
    local_rag: RAGService | None = None
    if config.compare_local:
        local_rag = RAGService(settings=Settings(rag_use_qdrant=False))

    dataset_path = config.dataset or (DATASET_DIR / "rag_questions.jsonl")
    rows: list[dict[str, Any]] = []
    for case in iter_jsonl(dataset_path, config.limit):
        query = str(case["query"])
        started = time.perf_counter()
        qdrant_sources = qdrant_store.search(query, top_k=config.top_k)
        elapsed = time.perf_counter() - started

        metrics = score_retrieval_case(case, qdrant_sources)

        if config.compare_local and local_rag is not None:
            local_sources = local_rag.retrieve(query, top_k=config.top_k)
            metrics["qdrant_vs_local_overlap"] = jaccard_overlap(qdrant_sources, local_sources)

        rows.append(
            {
                "id": case.get("id"),
                "query": query,
                "category": case.get("category"),
                "expected_recipes": case.get("expected_recipes", []),
                "expected_chunk_types": case.get("expected_chunk_types", []),
                "must_include": case.get("must_include", []),
                "sources": [source_to_dict(s) for s in qdrant_sources],
                "metrics": metrics,
                "elapsed_seconds": round(elapsed, 3),
            }
        )
    return rows


def run_local_retrieval(config: RunConfig) -> list[dict[str, Any]]:
    """Pure local lexical retrieval for comparison."""
    local_rag = RAGService(settings=Settings(rag_use_qdrant=False))
    dataset_path = config.dataset or (DATASET_DIR / "rag_questions.jsonl")
    rows: list[dict[str, Any]] = []
    for case in iter_jsonl(dataset_path, config.limit):
        query = str(case["query"])
        started = time.perf_counter()
        sources = local_rag.retrieve(query, top_k=config.top_k)
        elapsed = time.perf_counter() - started
        rows.append(
            {
                "id": case.get("id"),
                "query": query,
                "category": case.get("category"),
                "sources": [source_to_dict(s) for s in sources],
                "metrics": score_retrieval_case(case, sources),
                "elapsed_seconds": round(elapsed, 3),
            }
        )
    return rows


def run_qdrant_answer(config: RunConfig) -> list[dict[str, Any]]:
    """Qdrant retrieval + LLM answer – bypasses intent router."""
    settings = Settings(rag_use_qdrant=True)
    rag_service = RAGService(settings=settings)
    dataset_path = config.dataset or (DATASET_DIR / "rag_questions.jsonl")

    rows: list[dict[str, Any]] = []
    for case in iter_jsonl(dataset_path, config.limit):
        query = str(case["query"])
        started = time.perf_counter()
        result = rag_service.answer(query)
        elapsed = time.perf_counter() - started

        sources = result.sources[: config.top_k]
        metrics = score_retrieval_case(case, sources)
        metrics.update(score_answer_metrics(case, result.answer))

        rows.append(
            {
                "id": case.get("id"),
                "query": query,
                "category": case.get("category"),
                "answer": result.answer,
                "sources": [source_to_dict(s) for s in sources],
                "metrics": metrics,
                "elapsed_seconds": round(elapsed, 3),
            }
        )
    return rows


def run_qdrant_multiturn(config: RunConfig) -> list[dict[str, Any]]:
    """Multi-turn RAG retrieval – bypasses intent router entirely.

    Simulates session memory by building conversation_turns manually
    and calling RAGService.retrieve() for each turn.
    """
    settings = Settings(rag_use_qdrant=True)
    rag_service = RAGService(settings=settings)
    dataset_path = config.dataset or (DATASET_DIR / "rag_multiturn_questions.jsonl")

    rows: list[dict[str, Any]] = []
    for case in iter_jsonl(dataset_path, config.limit):
        turns: list[str] = case.get("turns", [])
        turn_results: list[dict[str, Any]] = []
        conversation_turns: list[dict[str, Any]] = []

        started = time.perf_counter()
        for turn_query in turns:
            sources = rag_service.retrieve(turn_query, top_k=config.top_k)
            turn_results.append(
                {
                    "query": turn_query,
                    "sources": [source_to_dict(s) for s in sources],
                    "chunk_types_hit": chunk_type_hit(
                        sources, case.get("expected_chunk_types", [])
                    ),
                }
            )
            # Build conversation context for next turn
            recipe_name = sources[0].recipe_name if sources else ""
            conversation_turns.append(
                {"query": turn_query, "active_recipe": recipe_name, "intent": "recipe_qa"}
            )
        elapsed = time.perf_counter() - started

        # Score on the LAST turn (the follow-up question)
        final_sources = turn_results[-1]["sources"] if turn_results else []
        final_sources_typed = [
            SourceChunk(
                recipe_id=s["recipe_id"],
                recipe_name=s["recipe_name"],
                chunk_type=ChunkType(s["chunk_type"]),
                content=s["content"],
                score=s.get("score", 0.0),
                metadata=s.get("metadata", {}),
            )
            for s in final_sources
        ]
        metrics: dict[str, Any] = {
            "chunk_type_hit_at_k": chunk_type_hit(
                final_sources_typed, case.get("expected_chunk_types", [])
            ),
            "must_include_pass": contains_all(
                "\n".join(s["content"] for s in final_sources),
                [str(v) for v in case.get("must_include", [])],
            ),
            "recipe_recall_at_k": any(
                s["recipe_name"] == case.get("expected_active_recipe", "")
                for s in final_sources
            ),
        }

        rows.append(
            {
                "id": case.get("id"),
                "expected_active_recipe": case.get("expected_active_recipe"),
                "expected_chunk_types": case.get("expected_chunk_types", []),
                "turns": turns,
                "turn_results": turn_results,
                "metrics": metrics,
                "elapsed_seconds": round(elapsed, 3),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

_RETRIEVAL_METRIC_NAMES = [
    "recipe_recall_at_k",
    "chunk_type_hit_at_k",
    "mrr",
    "source_coverage_pass",
    "source_keyword_recall",
]

_ANSWER_METRIC_NAMES = [
    "recipe_recall_at_k",
    "chunk_type_hit_at_k",
    "mrr",
    "source_coverage_pass",
    "source_keyword_recall",
    "answer_nonempty",
    "must_include_pass",
    "risk_keyword_absent",
    "groundedness_proxy_pass",
]

_MULTITURN_METRIC_NAMES = [
    "chunk_type_hit_at_k",
    "must_include_pass",
    "recipe_recall_at_k",
]


def score_retrieval_case(
    case: dict[str, Any],
    sources: list[SourceChunk],
) -> dict[str, Any]:
    expected_recipes = [str(v) for v in case.get("expected_recipes", [])]
    expected_chunk_types = case.get("expected_chunk_types", [case.get("category")])
    must_include = [str(v) for v in case.get("must_include", [])]

    recipe_rank = first_recipe_rank(sources, expected_recipes)
    source_text = "\n".join(s.content for s in sources)
    return {
        "recipe_recall_at_k": recipe_rank is not None,
        "mrr": 0.0 if recipe_rank is None else 1.0 / recipe_rank,
        "chunk_type_hit_at_k": chunk_type_hit(sources, expected_chunk_types),
        "source_keyword_recall": keyword_recall(source_text, must_include),
        "source_coverage_pass": contains_all(source_text, must_include),
    }


def score_answer_metrics(case: dict[str, Any], answer: str) -> dict[str, Any]:
    must_include = [str(v) for v in case.get("must_include", [])]
    risk_keywords = [str(v) for v in case.get("risk_keywords", [])]
    return {
        "answer_nonempty": bool(answer.strip()),
        "must_include_pass": contains_all(answer, must_include),
        "risk_keyword_absent": contains_none(answer, risk_keywords),
        "groundedness_proxy_pass": contains_all(answer, must_include),
    }


def first_recipe_rank(sources: list[SourceChunk], expected_recipes: list[str]) -> int | None:
    for index, source in enumerate(sources, start=1):
        if source.recipe_name in expected_recipes:
            return index
    return None


def chunk_type_hit(
    sources: list[SourceChunk], expected_types: Iterable[Any]
) -> bool:
    source_types = {normalize_chunk_type(s.chunk_type) for s in sources}
    expected = [str(v) for v in expected_types if v]
    if not expected:
        return True
    for expected_type in expected:
        aliases = CHUNK_TYPE_ALIASES.get(expected_type, {normalize_chunk_type(expected_type)})
        if source_types & aliases:
            return True
    return False


def jaccard_overlap(
    sources_a: list[SourceChunk], sources_b: list[SourceChunk]
) -> float:
    """Jaccard overlap of two source sets, identified by (recipe_id, chunk_type)."""
    keys_a = {(s.recipe_id, s.chunk_type) for s in sources_a}
    keys_b = {(s.recipe_id, s.chunk_type) for s in sources_b}
    if not keys_a and not keys_b:
        return 1.0
    if not keys_a or not keys_b:
        return 0.0
    return len(keys_a & keys_b) / len(keys_a | keys_b)


def keyword_recall(text: str, keywords: list[str]) -> float:
    keywords = [k for k in keywords if k]
    if not keywords:
        return 1.0
    return sum(1 for k in keywords if k in text) / len(keywords)


def contains_all(text: str, keywords: list[str]) -> bool:
    return all(k in text for k in keywords if k)


def contains_none(text: str, keywords: list[str]) -> bool:
    return all(k not in text for k in keywords if k)


# ---------------------------------------------------------------------------
# Summary with per-category breakdown
# ---------------------------------------------------------------------------


def summarize(
    rows: list[dict[str, Any]], metric_names: list[str]
) -> dict[str, Any]:
    overall = _summarize_rows(rows, metric_names)
    per_category: dict[str, dict[str, Any]] = {}
    categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        cat = row.get("category", "unknown")
        categories[cat].append(row)
    for cat, cat_rows in sorted(categories.items()):
        per_category[cat] = _summarize_rows(cat_rows, metric_names)
    return {"overall": overall, "per_category": per_category}


def _summarize_rows(rows: list[dict[str, Any]], metric_names: list[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {"total": len(rows)}
    for name in metric_names:
        values = [float(row["metrics"][name]) for row in rows if name in row["metrics"]]
        if not values:
            continue
        summary[name] = round(mean(values), 4)
    failed_ids = [
        row["id"]
        for row in rows
        if any(v is False for v in row.get("metrics", {}).values())
    ]
    summary["failed_ids"] = failed_ids[:50]
    summary["failed_count"] = len(failed_ids)
    return summary


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------


def source_to_dict(source: SourceChunk) -> dict[str, Any]:
    return {
        "recipe_id": source.recipe_id,
        "recipe_name": source.recipe_name,
        "chunk_type": normalize_enum(source.chunk_type),
        "score": source.score,
        "content": source.content,
        "metadata": normalize_value(source.metadata),
    }


def normalize_chunk_type(value: Any) -> str:
    raw = normalize_enum(value)
    return str(raw).split(".")[-1]


def normalize_enum(value: Any) -> Any:
    return getattr(value, "value", value)


def normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: normalize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_value(v) for v in value]
    return normalize_enum(value)


def iter_jsonl(path: Path, limit: int | None = None) -> Iterable[dict[str, Any]]:
    """Read JSON objects separated by blank lines (supports multi-line pretty-printed JSON)."""
    text = path.read_text(encoding="utf-8")
    count = 0
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if limit is not None and count >= limit:
            break
        yield json.loads(block)
        count += 1


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(normalize_value(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for i, row in enumerate(rows):
            if i > 0:
                f.write("\n")
            f.write(json.dumps(normalize_value(row), ensure_ascii=False, indent=2) + "\n")


def print_summary(summary_path: Path, outputs: dict[str, Any]) -> None:
    print(f"Summary: {summary_path}")
    for suite, result in outputs["results"].items():
        overall = result.get("overall", result)
        print(f"\n[{suite}] total={overall.get('total', '?')} failed={overall.get('failed_count', '?')}")
        for key, value in overall.items():
            if key not in {"total", "failed_ids", "failed_count"}:
                print(f"  - {key}: {value}")
        per_cat = result.get("per_category", {})
        if per_cat:
            print("  Per-category breakdown:")
            for cat, cat_summary in per_cat.items():
                metrics_str = ", ".join(
                    f"{k}={v}"
                    for k, v in cat_summary.items()
                    if k not in {"total", "failed_ids", "failed_count"}
                )
                print(f"    [{cat}] n={cat_summary['total']} | {metrics_str}")


if __name__ == "__main__":
    main()
