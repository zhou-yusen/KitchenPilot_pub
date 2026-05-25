from __future__ import annotations

import argparse
import json
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import uuid4

from kitchenpilot.agent import KitchenPilotAgent
from kitchenpilot.agent.state import AgentStateModel
from kitchenpilot.core.config import Settings
from kitchenpilot.core.embeddings import build_embedding_provider
from kitchenpilot.core.llm import build_chat_provider
from kitchenpilot.rag.service import RAGService
from kitchenpilot.schemas.enums import IntentType
from kitchenpilot.schemas.recipe import SourceChunk
from kitchenpilot.services.conversation_memory_service import conversation_memory_service

EVAL_ROOT = Path(__file__).resolve().parent
DATASET_DIR = EVAL_ROOT / "dataset"
RESULTS_DIR = EVAL_ROOT / "results"

CHUNK_TYPE_ALIASES = {
    "beginner_tip": {"step"},
    "failure_reason": {"failure"},
    "safety_note": {"safety"},
    "substitution": {"substitution"},
}


@dataclass(frozen=True)
class RunConfig:
    mode: str
    top_k: int
    limit: int | None
    llm_provider: str | None
    rag_use_qdrant: bool | None
    output_prefix: str


def main() -> None:
    args = parse_args()
    config = RunConfig(
        mode=args.mode,
        top_k=args.top_k,
        limit=args.limit,
        llm_provider=args.llm_provider,
        rag_use_qdrant=args.rag_use_qdrant,
        output_prefix=args.output_prefix or datetime.now().strftime("rag_%Y%m%d_%H%M%S"),
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    settings = build_settings(config)
    started = time.perf_counter()
    outputs: dict[str, Any] = {
        "config": {
            "mode": config.mode,
            "top_k": config.top_k,
            "limit": config.limit,
            "llm_provider": settings.llm_provider,
            "rag_use_qdrant": settings.rag_use_qdrant,
        },
        "results": {},
    }

    if config.mode in {"retrieval", "answer", "all"}:
        rag_service = RAGService(settings=settings)
        single_rows = run_single_turn(
            rag_service=rag_service,
            dataset_path=DATASET_DIR / "rag_questions.jsonl",
            config=config,
            include_answer=config.mode in {"answer", "all"},
        )
        outputs["results"]["single_turn"] = summarize_single_turn(single_rows)
        write_jsonl(RESULTS_DIR / f"{config.output_prefix}_single_turn.jsonl", single_rows)

    if config.mode in {"multiturn", "all"}:
        conversation_memory_service.clear()
        configure_agent_dependencies(settings)
        agent = KitchenPilotAgent()
        multi_rows = run_multiturn(
            agent=agent,
            dataset_path=DATASET_DIR / "rag_multiturn_questions.jsonl",
            config=config,
        )
        outputs["results"]["multiturn"] = summarize_multiturn(multi_rows)
        write_jsonl(RESULTS_DIR / f"{config.output_prefix}_multiturn.jsonl", multi_rows)

    outputs["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    summary_path = RESULTS_DIR / f"{config.output_prefix}_summary.json"
    write_json(summary_path, outputs)
    print_summary(summary_path, outputs)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run KitchenPilot fixed RAG benchmark.",
    )
    parser.add_argument(
        "--mode",
        choices=["retrieval", "answer", "multiturn", "all"],
        default="retrieval",
        help=(
            "retrieval only is fast and does not call the chat model; "
            "answer/all evaluate generated answers and may call Ollama/OpenAI."
        ),
    )
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None, help="Limit cases for smoke runs.")
    parser.add_argument(
        "--llm-provider",
        choices=["mock", "ollama", "openai"],
        default=None,
        help="Override LLM provider for answer/multiturn modes.",
    )
    parser.add_argument(
        "--rag-use-qdrant",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Override Qdrant retrieval. Use --no-rag-use-qdrant for local lexical smoke tests.",
    )
    parser.add_argument("--output-prefix", default="")
    return parser.parse_args()


def build_settings(config: RunConfig) -> Settings:
    updates: dict[str, Any] = {}
    if config.llm_provider:
        updates["llm_provider"] = config.llm_provider
    if config.rag_use_qdrant is not None:
        updates["rag_use_qdrant"] = config.rag_use_qdrant
    return Settings(**updates)


def configure_agent_dependencies(settings: Settings) -> None:
    """Apply CLI provider settings to module-level MVP services used by graph nodes."""
    import kitchenpilot.agent.nodes.intent_router as intent_router_module
    import kitchenpilot.agent.nodes.recipe_qa_node as recipe_qa_module

    recipe_qa_module.rag_service = RAGService(settings=settings)
    intent_router_module.router = intent_router_module.IntentRouter(
        chat_provider=build_chat_provider(settings),
        embedding_provider=build_embedding_provider(settings),
    )


def run_single_turn(
    *,
    rag_service: RAGService,
    dataset_path: Path,
    config: RunConfig,
    include_answer: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in iter_jsonl(dataset_path, config.limit):
        query = str(case["query"])
        started = time.perf_counter()
        if include_answer:
            result = rag_service.answer(query)
            sources = result.sources[: config.top_k]
            answer = result.answer
        else:
            sources = rag_service.retrieve(query, top_k=config.top_k)
            answer = ""
        elapsed = time.perf_counter() - started
        rows.append(
            {
                "id": case.get("id"),
                "query": query,
                "category": case.get("category"),
                "expected_recipes": case.get("expected_recipes", []),
                "expected_chunk_types": case.get("expected_chunk_types", [case.get("category")]),
                "must_include": case.get("must_include", []),
                "risk_keywords": case.get("risk_keywords", []),
                "answer": answer,
                "sources": [source_to_dict(source) for source in sources],
                "metrics": score_single_case(case, sources, answer, include_answer),
                "elapsed_seconds": round(elapsed, 3),
            }
        )
    return rows


def run_multiturn(
    *,
    agent: KitchenPilotAgent,
    dataset_path: Path,
    config: RunConfig,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in iter_jsonl(dataset_path, config.limit):
        session_id = f"eval_{uuid4().hex}"
        turn_results: list[dict[str, Any]] = []
        final_state: dict[str, Any] = {}
        started = time.perf_counter()
        for query in case.get("turns", []):
            final_state = agent.invoke(
                AgentStateModel(
                    query=str(query),
                    user_id="eval_user",
                    session_id=session_id,
                )
            )
            turn_results.append(state_to_turn_result(final_state))
        elapsed = time.perf_counter() - started
        rows.append(
            {
                "id": case.get("id"),
                "session_id": session_id,
                "turns": case.get("turns", []),
                "expected_active_recipe": case.get("expected_active_recipe"),
                "expected_intent": case.get("expected_intent"),
                "expected_rewritten_query_contains": case.get(
                    "expected_rewritten_query_contains", []
                ),
                "expected_chunk_types": case.get("expected_chunk_types", [case.get("category")]),
                "must_include": case.get("must_include", []),
                "risk_keywords": case.get("risk_keywords", []),
                "turn_results": turn_results,
                "metrics": score_multiturn_case(case, final_state),
                "elapsed_seconds": round(elapsed, 3),
            }
        )
    return rows


def score_single_case(
    case: dict[str, Any],
    sources: list[SourceChunk],
    answer: str,
    include_answer: bool,
) -> dict[str, Any]:
    expected_recipes = [str(value) for value in case.get("expected_recipes", [])]
    expected_chunk_types = case.get("expected_chunk_types", [case.get("category")])
    must_include = [str(value) for value in case.get("must_include", [])]
    risk_keywords = [str(value) for value in case.get("risk_keywords", [])]

    recipe_rank = first_recipe_rank(sources, expected_recipes)
    source_text = "\n".join(source.content for source in sources)
    metrics: dict[str, Any] = {
        "recipe_recall_at_k": recipe_rank is not None,
        "mrr": 0.0 if recipe_rank is None else 1.0 / recipe_rank,
        "chunk_type_hit_at_k": chunk_type_hit(sources, expected_chunk_types),
        "source_keyword_recall": keyword_recall(source_text, must_include),
        "source_coverage_pass": contains_all(source_text, must_include),
    }
    if include_answer:
        metrics.update(
            {
                "answer_nonempty": bool(answer.strip()),
                "must_include_pass": contains_all(answer, must_include),
                "risk_keyword_absent": contains_none(answer, risk_keywords),
                "groundedness_proxy_pass": contains_all(answer, must_include)
                and metrics["source_coverage_pass"],
                "no_hallucination_proxy_pass": contains_none(answer, risk_keywords),
            }
        )
    return metrics


def score_multiturn_case(case: dict[str, Any], final_state: dict[str, Any]) -> dict[str, Any]:
    expected_recipe = str(case.get("expected_active_recipe") or "")
    expected_intent = str(case.get("expected_intent") or IntentType.RECIPE_QA)
    rewritten_query = str(final_state.get("rewritten_query") or "")
    answer = str(final_state.get("final_answer") or "")
    sources = final_state.get("retrieved_context", [])
    return {
        "active_recipe_accuracy": str(final_state.get("active_recipe") or "") == expected_recipe,
        "follow_up_intent_accuracy": str(final_state.get("intent") or "") == expected_intent,
        "is_follow_up": bool(final_state.get("is_follow_up")),
        "rewrite_keyword_recall": keyword_recall(
            rewritten_query,
            [str(value) for value in case.get("expected_rewritten_query_contains", [])],
        ),
        "chunk_type_hit_at_k": chunk_type_hit(sources, case.get("expected_chunk_types", [])),
        "must_include_pass": contains_all(
            answer,
            [str(value) for value in case.get("must_include", [])],
        ),
        "risk_keyword_absent": contains_none(
            answer,
            [str(value) for value in case.get("risk_keywords", [])],
        ),
    }


def summarize_single_turn(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metric_names = [
        "recipe_recall_at_k",
        "chunk_type_hit_at_k",
        "source_keyword_recall",
        "source_coverage_pass",
        "mrr",
        "answer_nonempty",
        "must_include_pass",
        "risk_keyword_absent",
        "groundedness_proxy_pass",
        "no_hallucination_proxy_pass",
    ]
    return summarize_metrics(rows, metric_names)


def summarize_multiturn(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metric_names = [
        "active_recipe_accuracy",
        "follow_up_intent_accuracy",
        "is_follow_up",
        "rewrite_keyword_recall",
        "chunk_type_hit_at_k",
        "must_include_pass",
        "risk_keyword_absent",
    ]
    return summarize_metrics(rows, metric_names)


def summarize_metrics(rows: list[dict[str, Any]], metric_names: list[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {"total": len(rows)}
    for name in metric_names:
        values = [row["metrics"][name] for row in rows if name in row["metrics"]]
        if not values:
            continue
        numeric = [float(value) for value in values]
        summary[name] = round(mean(numeric), 4)
    failed_ids = [
        row["id"]
        for row in rows
        if any(value is False for value in row.get("metrics", {}).values())
    ]
    summary["failed_ids"] = failed_ids[:50]
    summary["failed_count"] = len(failed_ids)
    return summary


def source_to_dict(source: SourceChunk) -> dict[str, Any]:
    return {
        "recipe_id": source.recipe_id,
        "recipe_name": source.recipe_name,
        "chunk_type": normalize_enum(source.chunk_type),
        "score": source.score,
        "content": source.content,
        "metadata": normalize_value(source.metadata),
    }


def state_to_turn_result(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "query": state.get("query"),
        "intent": normalize_enum(state.get("intent")),
        "intent_confidence": state.get("intent_confidence"),
        "intent_source": state.get("intent_source"),
        "active_recipe": state.get("active_recipe"),
        "rewritten_query": state.get("rewritten_query"),
        "is_follow_up": state.get("is_follow_up"),
        "answer": state.get("final_answer"),
        "sources": [source_to_dict(source) for source in state.get("retrieved_context", [])],
        "execution_trace": state.get("execution_trace", []),
    }


def first_recipe_rank(sources: list[SourceChunk], expected_recipes: list[str]) -> int | None:
    for index, source in enumerate(sources, start=1):
        if source.recipe_name in expected_recipes:
            return index
    return None


def chunk_type_hit(sources: Iterable[SourceChunk], expected_types: Iterable[Any]) -> bool:
    source_types = {normalize_chunk_type(source.chunk_type) for source in sources}
    expected = [value for value in expected_types if value]
    if not expected:
        return True
    for expected_type in expected:
        aliases = CHUNK_TYPE_ALIASES.get(str(expected_type), {normalize_chunk_type(expected_type)})
        if source_types & aliases:
            return True
    return False


def keyword_recall(text: str, keywords: list[str]) -> float:
    keywords = [keyword for keyword in keywords if keyword]
    if not keywords:
        return 1.0
    return sum(1 for keyword in keywords if keyword in text) / len(keywords)


def contains_all(text: str, keywords: list[str]) -> bool:
    return all(keyword in text for keyword in keywords if keyword)


def contains_none(text: str, keywords: list[str]) -> bool:
    return all(keyword not in text for keyword in keywords if keyword)


def normalize_chunk_type(value: Any) -> str:
    raw = normalize_enum(value)
    return str(raw).split(".")[-1]


def normalize_enum(value: Any) -> Any:
    return getattr(value, "value", value)


def normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: normalize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
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
    with path.open("w", encoding="utf-8") as file:
        for i, row in enumerate(rows):
            if i > 0:
                file.write("\n")
            file.write(json.dumps(normalize_value(row), ensure_ascii=False, indent=2) + "\n")


def print_summary(summary_path: Path, outputs: dict[str, Any]) -> None:
    print(f"Summary: {summary_path}")
    for suite, summary in outputs["results"].items():
        print(f"\n[{suite}] total={summary['total']} failed={summary['failed_count']}")
        for key, value in summary.items():
            if key not in {"total", "failed_ids", "failed_count"}:
                print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
