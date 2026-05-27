"""RAGAS-based RAG evaluation for KitchenPilot.

Runs RAG pipeline against the test dataset, evaluates with RAGAS metrics
(faithfulness, answer_relevancy, context_precision, context_recall) plus
custom metrics, and outputs an HTML report.

Usage:
    uv run python evals/run_ragas_eval.py --limit 10
    uv run python evals/run_ragas_eval.py
    uv run python evals/run_ragas_eval.py --collection recipe_chunks_merged
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

from datasets import Dataset
from langchain_openai import ChatOpenAI
from ragas import evaluate as ragas_evaluate
from ragas.metrics._answer_relevance import answer_relevancy as ragas_answer_relevancy
from ragas.metrics._context_precision import context_precision as ragas_context_precision
from ragas.metrics._context_recall import context_recall as ragas_context_recall
from ragas.metrics._faithfulness import faithfulness as ragas_faithfulness

from kitchenpilot.core.config import Settings
from kitchenpilot.core.embeddings import (
    build_embedding_provider,
    cosine_similarity,
)
from kitchenpilot.rag.qdrant_store import QdrantRecipeStore
from kitchenpilot.rag.service import RAGService
from kitchenpilot.schemas.recipe import SourceChunk

EVAL_ROOT = Path(__file__).resolve().parent
DATASET_PATH = EVAL_ROOT / "dataset" / "rag_eval_split_250.json"
RESULTS_DIR = EVAL_ROOT / "results"
SEED_PATH = EVAL_ROOT.parent / "src" / "kitchenpilot" / "seed" / "data" / "recipes_initial.json"

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_recipe_id_map() -> dict[str, str]:
    recipes = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return {str(r["id"]): r["name"] for r in recipes}


def load_test_cases(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data["test_cases"]
    if limit:
        cases = cases[:limit]
    return cases


# ---------------------------------------------------------------------------
# RAG pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    rag_service: RAGService,
    test_cases: list[dict[str, Any]],
    id_map: dict[str, str],
) -> list[dict[str, Any]]:
    """Run RAG on each test case and collect results."""
    results: list[dict[str, Any]] = []
    for i, tc in enumerate(test_cases, 1):
        query = tc["query"]
        started = time.perf_counter()
        result = rag_service.answer(query)
        elapsed = time.perf_counter() - started

        sources = result.sources
        retrieved_ids = list(dict.fromkeys(str(s.recipe_id) for s in sources))
        relevant = set(str(r) for r in tc.get("relevant_record_ids", []))

        results.append({
            "test_id": tc.get("test_id", f"case_{i}"),
            "query": query,
            "answer": result.answer,
            "contexts": [s.content for s in sources],
            "ground_truth": tc.get("reference_answer", ""),
            "sources": sources,
            "retrieved_ids": retrieved_ids,
            "relevant_ids": list(relevant),
            "case_level": tc.get("case_level", "regular"),
            "question_type": tc.get("question_type", ""),
            "query_difficulty": tc.get("query_difficulty", "medium"),
            "must_include_facts": tc.get("must_include_facts", []),
            "elapsed_seconds": round(elapsed, 3),
        })

        hit = bool(set(retrieved_ids) & relevant)
        if i % 20 == 0 or i == len(test_cases):
            print(f"  [{i}/{len(test_cases)}] {tc.get('test_id','')} hit={hit} {elapsed:.1f}s")

    return results


# ---------------------------------------------------------------------------
# RAGAS evaluation
# ---------------------------------------------------------------------------

def run_ragas(results: list[dict[str, Any]], settings: Settings) -> dict[str, float]:
    """Run RAGAS metrics on the collected results."""
    from langchain_openai import OpenAIEmbeddings
    from openai import OpenAI
    from ragas.llms import llm_factory

    judge_llm = llm_factory(
        settings.mimo_model,
        client=OpenAI(
            base_url=settings.mimo_base_url,
            api_key=settings.mimo_api_key,
            max_retries=5,
            timeout=120.0,
        ),
        max_tokens=4096,
    )

    # answer_relevancy needs LangChain embeddings (embed_query method)
    lc_embeddings = OpenAIEmbeddings(
        model=settings.ollama_embedding_model,
        base_url=f"{settings.ollama_base_url}/v1",
        api_key="ollama",
        check_embedding_ctx_length=False,
    )

    dataset = Dataset.from_dict({
        "user_input": [r["query"] for r in results],
        "response": [r["answer"] for r in results],
        "retrieved_contexts": [r["contexts"] for r in results],
        "reference": [r["ground_truth"] for r in results],
    })

    # Set embeddings on answer_relevancy metric
    ragas_answer_relevancy.embeddings = lc_embeddings

    metrics = [
        ragas_faithfulness,
        ragas_answer_relevancy,
        ragas_context_precision,
        ragas_context_recall,
    ]

    print("Running RAGAS evaluation (this may take a few minutes)...")
    ragas_result = ragas_evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=judge_llm,
        show_progress=True,
        batch_size=5,
    )

    # Extract per-metric scores
    scores: dict[str, float] = {}
    df = ragas_result.to_pandas()
    for metric_name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        if metric_name in df.columns:
            vals = df[metric_name].dropna().tolist()
            scores[metric_name] = round(mean(vals), 4) if vals else 0.0

    # Per-case scores
    for i, row in df.iterrows():
        if i < len(results):
            results[i]["ragas_scores"] = {
                m: round(float(row[m]), 4) if m in row.index and not _is_nan(row[m]) else None
                for m in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
            }

    return scores


def _is_nan(val: Any) -> bool:
    try:
        import math
        return math.isnan(float(val))
    except (TypeError, ValueError):
        return val is None


# ---------------------------------------------------------------------------
# Custom metrics
# ---------------------------------------------------------------------------

def compute_custom_metrics(results: list[dict[str, Any]]) -> dict[str, float]:
    """Compute custom metrics not covered by RAGAS."""
    hits = 0
    similarities: list[float] = []
    coverages: list[float] = []
    hard_hits = 0
    hard_total = 0
    fact_hits = 0
    fact_total = 0

    embedding_provider = build_embedding_provider()

    # Pre-embed reference answers in batch
    ref_texts = list({r["ground_truth"] for r in results if r["ground_truth"]})
    ref_cache: dict[str, list[float]] = {}
    if ref_texts:
        for start in range(0, len(ref_texts), 32):
            batch = ref_texts[start : start + 32]
            vecs = embedding_provider.embed(batch)
            for t, v in zip(batch, vecs, strict=True):
                ref_cache[t] = v

    for r in results:
        retrieved = set(r["retrieved_ids"])
        relevant = set(r["relevant_ids"])
        hit = bool(retrieved & relevant)
        if hit:
            hits += 1

        # Answer similarity
        answer = r["answer"]
        gt = r["ground_truth"]
        if answer.strip() and gt.strip():
            a_vec = embedding_provider.embed([answer])[0]
            g_vec = ref_cache.get(gt) or embedding_provider.embed([gt])[0]
            similarities.append(cosine_similarity(a_vec, g_vec))

        # Recipe coverage
        answer_text = r["answer"]
        relevant_names = set()
        for rid in relevant:
            name = _get_recipe_name(rid)
            if name:
                relevant_names.add(name)
        if relevant_names:
            found = sum(1 for n in relevant_names if n in answer_text)
            coverages.append(found / len(relevant_names))

        # Hard case
        if r["case_level"] == "hard":
            hard_total += 1
            if hit:
                hard_hits += 1

        # Must-include facts
        facts = r.get("must_include_facts", [])
        if facts:
            fact_total += 1
            if all(f in answer_text for f in facts):
                fact_hits += 1

    total = len(results)
    return {
        "retrieval_hit_rate": round(hits / total, 4) if total else 0.0,
        "answer_similarity": round(mean(similarities), 4) if similarities else 0.0,
        "recipe_coverage": round(mean(coverages), 4) if coverages else 0.0,
        "hard_case_accuracy": round(hard_hits / hard_total, 4) if hard_total else 0.0,
        "must_include_fact_rate": round(fact_hits / fact_total, 4) if fact_total else 0.0,
    }


_RECIPE_NAMES: dict[str, str] = {}

def _get_recipe_name(rid: str) -> str:
    global _RECIPE_NAMES
    if not _RECIPE_NAMES:
        _RECIPE_NAMES = load_recipe_id_map()
    return _RECIPE_NAMES.get(rid, "")


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def generate_html_report(
    results: list[dict[str, Any]],
    ragas_scores: dict[str, float],
    custom_scores: dict[str, float],
    elapsed: float,
    output_path: Path,
) -> None:
    """Generate a self-contained HTML report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Per-type breakdown
    per_type: dict[str, list[dict]] = defaultdict(list)
    per_level: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        per_type[r["question_type"]].append(r)
        per_level[r["case_level"]].append(r)

    html = _build_html(results, ragas_scores, custom_scores, per_type, per_level, elapsed)
    output_path.write_text(html, encoding="utf-8")
    print(f"HTML report: {output_path}")


def _score_color(val: float | None) -> str:
    if val is None:
        return "#999"
    if val >= 0.7:
        return "#2ecc71"
    if val >= 0.4:
        return "#f39c12"
    return "#e74c3c"


def _build_html(
    results: list[dict[str, Any]],
    ragas_scores: dict[str, float],
    custom_scores: dict[str, float],
    per_type: dict[str, list[dict]],
    per_level: dict[str, list[dict]],
    elapsed: float,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(results)

    # Summary cards
    all_metrics = {**ragas_scores, **custom_scores}
    summary_cards = ""
    for name, val in all_metrics.items():
        color = _score_color(val)
        label = name.replace("_", " ").title()
        summary_cards += f"""
        <div class="card">
            <div class="card-value" style="color:{color}">{val:.4f}</div>
            <div class="card-label">{label}</div>
        </div>"""

    # Per-type table
    type_rows = _build_breakdown_rows(per_type, "question_type")
    level_rows = _build_breakdown_rows(per_level, "case_level")

    # Detail rows
    detail_rows = ""
    for i, r in enumerate(results):
        ragas = r.get("ragas_scores", {})
        metrics_html = ""
        for m_name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
            m_val = ragas.get(m_name)
            color = _score_color(m_val)
            val_str = f"{m_val:.3f}" if m_val is not None else "N/A"
            metrics_html += f'<span class="metric" style="color:{color}">{m_name}: {val_str}</span> '

        contexts_preview = "<br>".join(
            f"<small>{c[:100]}...</small>" for c in r["contexts"][:3]
        ) if r["contexts"] else "<small>None</small>"

        answer_preview = r["answer"][:300] + ("..." if len(r["answer"]) > 300 else "")

        detail_rows += f"""
        <tr>
            <td>{r['test_id']}</td>
            <td>{r['question_type']}</td>
            <td>{r['case_level']}</td>
            <td class="query">{r['query']}</td>
            <td class="answer">{answer_preview}</td>
            <td>{metrics_html}</td>
            <td>{r['elapsed_seconds']:.1f}s</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>KitchenPilot RAG Evaluation Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f6fa; color: #2d3436; }}
h1 {{ color: #2d3436; border-bottom: 3px solid #6c5ce7; padding-bottom: 10px; }}
h2 {{ color: #6c5ce7; margin-top: 30px; }}
.summary {{ display: flex; flex-wrap: wrap; gap: 16px; margin: 20px 0; }}
.card {{ background: white; border-radius: 12px; padding: 20px 24px; min-width: 160px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }}
.card-value {{ font-size: 28px; font-weight: 700; }}
.card-label {{ font-size: 13px; color: #636e72; margin-top: 4px; }}
table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin: 16px 0; }}
th {{ background: #6c5ce7; color: white; padding: 10px 12px; text-align: left; font-size: 13px; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #eee; font-size: 13px; vertical-align: top; }}
tr:hover {{ background: #f8f9ff; }}
.query {{ max-width: 200px; }}
.answer {{ max-width: 300px; font-size: 12px; color: #636e72; }}
.metric {{ display: inline-block; font-size: 11px; font-weight: 600; margin-right: 8px; }}
.footer {{ margin-top: 40px; padding: 16px; text-align: center; color: #b2bec3; font-size: 12px; }}
</style>
</head>
<body>
<h1>KitchenPilot RAG Evaluation Report</h1>
<p>Generated: {now} | Cases: {total} | Elapsed: {elapsed:.1f}s</p>

<h2>Overall Metrics</h2>
<div class="summary">{summary_cards}</div>

<h2>By Question Type</h2>
<table>
<tr><th>Type</th><th>N</th><th>Faithfulness</th><th>Answer Relevancy</th><th>Context Precision</th><th>Context Recall</th><th>Hit Rate</th></tr>
{type_rows}
</table>

<h2>By Case Level</h2>
<table>
<tr><th>Level</th><th>N</th><th>Faithfulness</th><th>Answer Relevancy</th><th>Context Precision</th><th>Context Recall</th><th>Hit Rate</th></tr>
{level_rows}
</table>

<h2>Detail Results</h2>
<table>
<tr><th>ID</th><th>Type</th><th>Level</th><th>Query</th><th>Answer</th><th>RAGAS Scores</th><th>Time</th></tr>
{detail_rows}
</table>

<div class="footer">KitchenPilot RAG Evaluation | Powered by RAGAS</div>
</body>
</html>"""


def _build_breakdown_rows(
    groups: dict[str, list[dict]], group_key: str
) -> str:
    rows = ""
    for key in sorted(groups.keys()):
        cases = groups[key]
        n = len(cases)
        ragas_vals: dict[str, list[float]] = defaultdict(list)
        hits = 0
        for c in cases:
            for m in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
                v = (c.get("ragas_scores") or {}).get(m)
                if v is not None:
                    ragas_vals[m].append(v)
            if bool(set(c["retrieved_ids"]) & set(c["relevant_ids"])):
                hits += 1

        def _avg(metric: str) -> str:
            vals = ragas_vals.get(metric, [])
            if not vals:
                return '<td style="color:#999">N/A</td>'
            avg = mean(vals)
            color = _score_color(avg)
            return f'<td style="color:{color};font-weight:600">{avg:.4f}</td>'

        hit_rate = hits / n if n else 0
        hit_color = _score_color(hit_rate)
        rows += f"""<tr>
            <td><b>{key}</b></td><td>{n}</td>
            {_avg("faithfulness")}{_avg("answer_relevancy")}{_avg("context_precision")}{_avg("context_recall")}
            <td style="color:{hit_color};font-weight:600">{hit_rate:.4f}</td>
        </tr>"""
    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RAGAS RAG evaluation.")
    parser.add_argument("--limit", type=int, default=None, help="Max cases to evaluate.")
    parser.add_argument("--collection", default=None, help="Qdrant collection override.")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--output", type=Path, default=None, help="HTML report output path.")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    settings = Settings(rag_use_qdrant=True)

    if args.collection:
        settings = settings.model_copy(update={"qdrant_collection": args.collection})

    id_map = load_recipe_id_map()
    test_cases = load_test_cases(args.dataset, args.limit)
    print(f"Loaded {len(test_cases)} test cases from {args.dataset}")
    print(f"Collection: {settings.qdrant_collection}")

    rag_service = RAGService(settings=settings)
    started = time.perf_counter()

    # Step 1: Run RAG pipeline
    print("\n--- Running RAG pipeline ---")
    results = run_pipeline(rag_service, test_cases, id_map)

    # Step 2: RAGAS evaluation
    print("\n--- Running RAGAS evaluation ---")
    ragas_scores = run_ragas(results, settings)
    print(f"RAGAS scores: {ragas_scores}")

    # Step 3: Custom metrics
    print("\n--- Computing custom metrics ---")
    custom_scores = compute_custom_metrics(results)
    print(f"Custom scores: {custom_scores}")

    elapsed = time.perf_counter() - started

    # Step 4: HTML report
    output_path = args.output or (RESULTS_DIR / "ragas_report.html")
    generate_html_report(results, ragas_scores, custom_scores, elapsed, output_path)

    # Summary
    print(f"\n{'='*60}")
    print(f"Total: {len(results)} cases | Elapsed: {elapsed:.1f}s")
    print("RAGAS:", " | ".join(f"{k}={v}" for k, v in ragas_scores.items()))
    print("Custom:", " | ".join(f"{k}={v}" for k, v in custom_scores.items()))


if __name__ == "__main__":
    main()
