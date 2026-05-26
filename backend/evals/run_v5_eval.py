"""KitchenPilot RAG evaluation against the v5 test dataset.

Reads the user-provided test set (rag_testset_recipes_v5_repaired.json)
and evaluates RAG retrieval + answer quality across 8 evaluation modes.

Usage:
    uv run python evals/run_v5_eval.py --mode retrieval
    uv run python evals/run_v5_eval.py --mode answer
    uv run python evals/run_v5_eval.py --mode retrieval --limit 10
    uv run python evals/run_v5_eval.py --mode answer --limit 10
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

from kitchenpilot.core.config import Settings
from kitchenpilot.core.embeddings import EmbeddingProvider, build_embedding_provider, cosine_similarity
from kitchenpilot.rag.qdrant_store import QdrantRecipeStore
from kitchenpilot.rag.service import RAGService
from kitchenpilot.schemas.recipe import SourceChunk

EVAL_ROOT = Path(__file__).resolve().parent
SEED_DATA_DIR = EVAL_ROOT.parent / "src" / "kitchenpilot" / "seed" / "data"
DEFAULT_DATASET = SEED_DATA_DIR / "rag_testset_recipes_v5_repaired.json"
RESULTS_DIR = EVAL_ROOT / "results"
SEED_PATH = SEED_DATA_DIR / "recipes_initial.json"

# ---------------------------------------------------------------------------
# Recipe ID ↔ Name mapping
# ---------------------------------------------------------------------------

def load_recipe_id_map() -> dict[str, str]:
    """Build {recipe_id_str: recipe_name} from seed data."""
    recipes = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return {str(r["id"]): r["name"] for r in recipes}


def load_recipe_constraints() -> dict[str, dict[str, Any]]:
    """Build {recipe_id_str: {name, time_minutes, difficulty}} from seed data."""
    recipes = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return {
        str(r["id"]): {
            "name": r["name"],
            "time_minutes": r.get("time_minutes", 999),
            "difficulty": r.get("difficulty", "medium"),
        }
        for r in recipes
    }

# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    test_id: str
    subset: str
    hard_category: str | None
    query: str
    question_type: str
    test_difficulty: str
    evaluation_mode: str
    relevant_record_ids: list[str]
    primary_record_ids: list[str]
    acceptable_record_ids: list[str]
    reference_answer: str
    evidence: list[dict[str, Any]]
    evaluation_points: list[str]
    expected_behavior: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TestCase":
        return cls(
            test_id=d["test_id"],
            subset=d.get("subset", "regular"),
            hard_category=d.get("hard_category"),
            query=d["query"],
            question_type=d["question_type"],
            test_difficulty=d.get("test_difficulty", "medium"),
            evaluation_mode=d["evaluation_mode"],
            relevant_record_ids=[str(r) for r in d.get("relevant_record_ids", [])],
            primary_record_ids=[str(r) for r in d.get("primary_record_ids", [])],
            acceptable_record_ids=[str(r) for r in d.get("acceptable_record_ids", [])],
            reference_answer=d.get("reference_answer", ""),
            evidence=d.get("evidence", []),
            evaluation_points=d.get("evaluation_points", []),
            expected_behavior=d.get("expected_behavior", ""),
        )


def load_test_cases(path: Path, limit: int | None = None) -> list[TestCase]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = [TestCase.from_dict(d) for d in data["test_cases"]]
    if limit:
        cases = cases[:limit]
    return cases


# ---------------------------------------------------------------------------
# Semantic scorer (embedding-based similarity)
# ---------------------------------------------------------------------------

class SemanticScorer:
    """Pre-compute reference answer embeddings and score via cosine similarity."""

    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self._provider = embedding_provider
        self._cache: dict[str, list[float]] = {}

    def warm_up(self, reference_answers: list[str], batch_size: int = 32) -> None:
        """Batch-embed all unique reference answers to populate cache."""
        unique = list({text for text in reference_answers if text.strip()})
        if not unique:
            return
        for start in range(0, len(unique), batch_size):
            batch = unique[start : start + batch_size]
            vectors = self._provider.embed(batch)
            for text, vec in zip(batch, vectors, strict=True):
                self._cache[text] = vec
            print(f"  Embedded {min(start + batch_size, len(unique))}/{len(unique)}")

    def _get_vector(self, text: str) -> list[float]:
        if text in self._cache:
            return self._cache[text]
        vec = self._provider.embed([text])[0]
        self._cache[text] = vec
        return vec

    def similarity(self, text_a: str, text_b: str) -> float:
        """Compute cosine similarity between two texts."""
        if not text_a.strip() or not text_b.strip():
            return 0.0
        vec_a = self._get_vector(text_a)
        vec_b = self._get_vector(text_b)
        return cosine_similarity(vec_a, vec_b)

    def retrieval_similarities(self, query: str, chunk_contents: list[str]) -> list[float]:
        """Compute cosine similarity between query and each chunk content."""
        if not chunk_contents:
            return []
        query_vec = self._get_vector(query)
        chunk_vecs = [self._get_vector(c) for c in chunk_contents]
        return [cosine_similarity(query_vec, cv) for cv in chunk_vecs]

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RunConfig:
    mode: str            # retrieval | answer
    top_k: int
    limit: int | None
    dataset: Path
    output_prefix: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RAG v5 test set evaluation.")
    parser.add_argument("--mode", choices=["retrieval", "answer"], default="retrieval",
                        help="retrieval: pure vector search. answer: retrieval + LLM generation.")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
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
        dataset=args.dataset,
        output_prefix=args.output_prefix or datetime.now().strftime("v5_%Y%m%d_%H%M%S"),
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    id_map = load_recipe_id_map()
    constraints = load_recipe_constraints()
    test_cases = load_test_cases(config.dataset, config.limit)

    print(f"Loaded {len(test_cases)} test cases from {config.dataset}")
    print(f"Mode: {config.mode}  |  Top-K: {config.top_k}")

    started = time.perf_counter()

    settings = Settings(rag_use_qdrant=True)
    scorer = SemanticScorer(build_embedding_provider(settings))
    # Pre-embed all reference answers for caching
    ref_answers = [tc.reference_answer for tc in test_cases]
    print("Pre-computing reference answer embeddings...")
    scorer.warm_up(ref_answers)
    print(f"  Cached {len(scorer._cache)} embeddings")

    if config.mode == "retrieval":
        rows = run_retrieval(config, test_cases, id_map, scorer)
    else:
        rows = run_answer(config, test_cases, id_map, constraints, scorer)

    elapsed = time.perf_counter() - started

    # Collect metric names
    metric_names: set[str] = set()
    for row in rows:
        metric_names.update(row["metrics"].keys())

    summary = build_summary(rows, sorted(metric_names))
    summary["elapsed_seconds"] = round(elapsed, 3)
    summary["config"] = {
        "mode": config.mode,
        "top_k": config.top_k,
        "limit": config.limit,
    }

    detail_path = RESULTS_DIR / f"{config.output_prefix}_v5_detail.jsonl"
    summary_path = RESULTS_DIR / f"{config.output_prefix}_v5_summary.json"

    write_jsonl(detail_path, rows)
    write_json(summary_path, summary)

    print(f"\n{'='*60}")
    print_summary(summary)
    print(f"\nDetail: {detail_path}")
    print(f"Summary: {summary_path}")

# ---------------------------------------------------------------------------
# Run modes
# ---------------------------------------------------------------------------

def run_retrieval(
    config: RunConfig,
    test_cases: list[TestCase],
    id_map: dict[str, str],
    scorer: SemanticScorer,
) -> list[dict[str, Any]]:
    """Pure Qdrant vector retrieval - no LLM."""
    settings = Settings(rag_use_qdrant=True)
    store = QdrantRecipeStore(settings=settings)

    rows: list[dict[str, Any]] = []
    for i, tc in enumerate(test_cases, 1):
        started = time.perf_counter()
        sources = store.search(tc.query, top_k=config.top_k)
        elapsed = time.perf_counter() - started

        metrics = score_retrieval(tc, sources, id_map, scorer)

        rows.append({
            "test_id": tc.test_id,
            "subset": tc.subset,
            "question_type": tc.question_type,
            "test_difficulty": tc.test_difficulty,
            "evaluation_mode": tc.evaluation_mode,
            "query": tc.query,
            "relevant_record_ids": tc.relevant_record_ids,
            "retrieved_recipe_ids": list(dict.fromkeys(str(s.recipe_id) for s in sources)),
            "retrieved_recipe_names": [s.recipe_name for s in sources],
            "sources": [source_to_dict(s) for s in sources],
            "metrics": metrics,
            "elapsed_seconds": round(elapsed, 3),
        })

        # Progress
        status = "✓" if all(v for v in metrics.values() if isinstance(v, bool)) else "✗"
        if i % 20 == 0 or i == len(test_cases):
            print(f"  [{i}/{len(test_cases)}] {tc.test_id} {status}")

    return rows


def run_answer(
    config: RunConfig,
    test_cases: list[TestCase],
    id_map: dict[str, str],
    constraints: dict[str, dict[str, Any]],
    scorer: SemanticScorer,
) -> list[dict[str, Any]]:
    """Qdrant retrieval + LLM answer generation."""
    settings = Settings(rag_use_qdrant=True)
    rag = RAGService(settings=settings)

    rows: list[dict[str, Any]] = []
    for i, tc in enumerate(test_cases, 1):
        started = time.perf_counter()
        result = rag.answer(tc.query)
        elapsed = time.perf_counter() - started

        sources = result.sources[:config.top_k]
        answer = result.answer

        # Retrieval metrics
        metrics = score_retrieval(tc, sources, id_map, scorer)
        # Answer metrics
        metrics.update(score_answer(tc, answer, id_map, constraints, scorer))

        rows.append({
            "test_id": tc.test_id,
            "subset": tc.subset,
            "question_type": tc.question_type,
            "test_difficulty": tc.test_difficulty,
            "evaluation_mode": tc.evaluation_mode,
            "query": tc.query,
            "answer": answer,
            "relevant_record_ids": tc.relevant_record_ids,
            "retrieved_recipe_ids": list(dict.fromkeys(str(s.recipe_id) for s in sources)),
            "retrieved_recipe_names": [s.recipe_name for s in sources],
            "sources": [source_to_dict(s) for s in sources],
            "metrics": metrics,
            "elapsed_seconds": round(elapsed, 3),
        })

        status = "✓" if all(v for v in metrics.values() if isinstance(v, bool)) else "✗"
        if i % 20 == 0 or i == len(test_cases):
            print(f"  [{i}/{len(test_cases)}] {tc.test_id} {status}")

    return rows

# ---------------------------------------------------------------------------
# Retrieval scoring
# ---------------------------------------------------------------------------

def score_retrieval(
    tc: TestCase,
    sources: list[SourceChunk],
    id_map: dict[str, str],
    scorer: SemanticScorer,
) -> dict[str, Any]:
    """Score retrieval results against a test case."""
    retrieved_ids = list(dict.fromkeys(str(s.recipe_id) for s in sources))
    relevant = set(tc.relevant_record_ids)

    # Did we find at least one relevant record?
    hit = bool(set(retrieved_ids) & relevant)

    # Rank of first relevant result (1-indexed)
    first_rank = None
    for idx, rid in enumerate(retrieved_ids, 1):
        if rid in relevant:
            first_rank = idx
            break

    # For multi-record: how many relevant records found?
    found = set(retrieved_ids) & relevant
    coverage = len(found) / len(relevant) if relevant else 1.0

    # For acceptable_record_ids: broader match
    acceptable = set(tc.acceptable_record_ids) if tc.acceptable_record_ids else relevant
    acceptable_found = set(retrieved_ids) & acceptable
    acceptable_coverage = len(acceptable_found) / len(acceptable) if acceptable else 1.0

    # Semantic retrieval quality: query ↔ chunk content similarity
    chunk_contents = [s.content for s in sources]
    sims = scorer.retrieval_similarities(tc.query, chunk_contents)

    return {
        "retrieval_hit": hit,
        "mrr": 0.0 if first_rank is None else 1.0 / first_rank,
        "retrieval_recall": hit,
        "relevant_coverage": round(coverage, 3),
        "acceptable_coverage": round(acceptable_coverage, 3),
        "avg_retrieval_similarity": round(mean(sims), 4) if sims else 0.0,
        "max_retrieval_similarity": round(max(sims), 4) if sims else 0.0,
    }

# ---------------------------------------------------------------------------
# Answer scoring (8 evaluation modes)
# ---------------------------------------------------------------------------

# Refusal indicators for unanswerable questions
REFUSAL_PATTERNS = [
    "无法回答", "不能回答", "不确定", "缺少", "没有找到", "数据不足",
    "知识库里", "暂时没有", "没有足够", "无法确认", "建议",
    "信息不够", "无法提供", "未找到", "缺失", "不属于",
    "抱歉", "sorry", "无法判断", "not enough",
]

# Safety keywords that should appear in safety answers
SAFETY_KEYWORDS = [
    "熟", "过敏", "安全", "风险", "注意", "温度", "保存",
    "卫生", "加热", "煮", "细菌", "变质", "干净",
    "生", "未熟", "交叉", "消毒", "洗手",
]


def score_answer(
    tc: TestCase,
    answer: str,
    id_map: dict[str, str],
    constraints: dict[str, dict[str, Any]],
    scorer: SemanticScorer,
) -> dict[str, Any]:
    """Score answer quality based on evaluation_mode using semantic similarity."""
    mode = tc.evaluation_mode

    # Common: semantic similarity between answer and reference
    ref_sim = scorer.similarity(answer, tc.reference_answer) if tc.reference_answer else 0.0
    base = {
        "answer_nonempty": bool(answer.strip()),
        "answer_semantic_similarity": round(ref_sim, 4),
    }

    if mode == "grounded_answer":
        return base

    if mode == "substitution_check":
        return base

    if mode == "safety_grounded_answer":
        safety_hit = sum(1 for k in SAFETY_KEYWORDS if k in answer)
        base["safety_keyword_count"] = safety_hit
        base["answer_has_safety"] = safety_hit >= 1
        return base

    if mode in ("multi_answer", "multi_record_comparison", "disambiguation"):
        acceptable = set(tc.acceptable_record_ids or tc.relevant_record_ids)
        names_found = sum(1 for rid in acceptable if id_map.get(rid, "") in answer)
        base["answer_multi_coverage"] = round(names_found / len(acceptable), 3) if acceptable else 0.0
        if mode == "multi_record_comparison":
            comparison_words = ["不同", "区别", "相比", "更", "而", "则", "但", "vs", "对比"]
            base["answer_has_comparison"] = any(w in answer for w in comparison_words)
        if mode == "disambiguation":
            clarify_words = ["哪个", "是指", "区分", "有两种", "有多种", "可能", "具体", "请问"]
            base["answer_clarifies"] = any(w in answer for w in clarify_words)
        return base

    if mode == "constraint_filter":
        relevant = set(tc.relevant_record_ids)
        time_match = re.search(r"(\d+)\s*分钟", tc.query)
        max_time = int(time_match.group(1)) if time_match else None
        mentioned = 0
        valid = 0
        for rid in relevant:
            name = id_map.get(rid, "")
            if name and name in answer:
                mentioned += 1
                if max_time and rid in constraints:
                    if constraints[rid]["time_minutes"] <= max_time:
                        valid += 1
                else:
                    valid += 1
        base["constraint_mentioned"] = round(mentioned / len(relevant), 3) if relevant else 0.0
        base["constraint_valid"] = round(valid / max(mentioned, 1), 3)
        return base

    if mode == "grounded_unanswerable":
        has_refusal = any(p in answer for p in REFUSAL_PATTERNS)
        confident_claims = ["是 ", "为 ", "等于", "当然是", "肯定是"]
        has_confident_claim = any(p in answer for p in confident_claims)
        base["correct_refusal"] = has_refusal
        base["no_hallucination"] = not has_confident_claim
        return base

    return base

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def build_summary(rows: list[dict[str, Any]], metric_names: list[str]) -> dict[str, Any]:
    """Build summary with overall + per-mode + per-type + per-difficulty breakdowns."""
    overall = _summarize_rows(rows, metric_names)

    per_mode: dict[str, Any] = {}
    per_type: dict[str, Any] = {}
    per_difficulty: dict[str, Any] = {}
    per_subset: dict[str, Any] = {}

    groups: dict[str, dict[str, list[dict[str, Any]]]] = {
        "mode": defaultdict(list),
        "type": defaultdict(list),
        "difficulty": defaultdict(list),
        "subset": defaultdict(list),
    }

    for row in rows:
        groups["mode"][row["evaluation_mode"]].append(row)
        groups["type"][row["question_type"]].append(row)
        groups["difficulty"][row["test_difficulty"]].append(row)
        groups["subset"][row["subset"]].append(row)

    for key, bucket in sorted(groups["mode"].items()):
        per_mode[key] = _summarize_rows(bucket, metric_names)
    for key, bucket in sorted(groups["type"].items()):
        per_type[key] = _summarize_rows(bucket, metric_names)
    for key, bucket in sorted(groups["difficulty"].items()):
        per_difficulty[key] = _summarize_rows(bucket, metric_names)
    for key, bucket in sorted(groups["subset"].items()):
        per_subset[key] = _summarize_rows(bucket, metric_names)

    return {
        "overall": overall,
        "per_evaluation_mode": per_mode,
        "per_question_type": per_type,
        "per_difficulty": per_difficulty,
        "per_subset": per_subset,
    }


def _summarize_rows(rows: list[dict[str, Any]], metric_names: list[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {"total": len(rows)}
    for name in metric_names:
        values = []
        for row in rows:
            m = row.get("metrics", {})
            if name in m:
                values.append(float(m[name]))
        if values:
            summary[name] = round(mean(values), 4)
    failed_ids = [
        row["test_id"] for row in rows
        if not row.get("metrics", {}).get("retrieval_hit", True)
    ]
    summary["retrieval_miss_ids"] = failed_ids[:50]
    summary["retrieval_miss_count"] = len(failed_ids)
    return summary

# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------

def source_to_dict(source: SourceChunk) -> dict[str, Any]:
    return {
        "recipe_id": source.recipe_id,
        "recipe_name": source.recipe_name,
        "chunk_type": getattr(source.chunk_type, "value", str(source.chunk_type)),
        "score": round(source.score, 4),
        "content": source.content[:200],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for i, row in enumerate(rows):
            if i > 0:
                f.write("\n")
            f.write(json.dumps(row, ensure_ascii=False, indent=2) + "\n")


def print_summary(summary: dict[str, Any]) -> None:
    overall = summary.get("overall", {})
    print(f"\nOverall: {overall.get('total', '?')} cases  |  retrieval misses: {overall.get('retrieval_miss_count', '?')}")
    print("  Metrics:")
    for k, v in overall.items():
        if k not in {"total", "retrieval_miss_ids", "retrieval_miss_count"}:
            print(f"    {k}: {v}")

    for section in ["per_evaluation_mode", "per_question_type", "per_difficulty", "per_subset"]:
        data = summary.get(section, {})
        if not data:
            continue
        label = section.replace("per_", "").replace("_", " ").title()
        print(f"\n  {label}:")
        for key, stats in data.items():
            metrics = ", ".join(
                f"{k}={v}" for k, v in stats.items()
                if k not in {"total", "retrieval_miss_ids", "retrieval_miss_count"}
            )
            print(f"    [{key}] n={stats['total']} | {metrics}")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
