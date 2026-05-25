"""Generate RAG evaluation datasets from the enriched seed data.

Reads recipes_initial.json and produces:
  - rag_questions.jsonl     (single-turn, 3 questions per recipe)
  - rag_multiturn_questions.jsonl (multi-turn follow-ups, 1 per recipe)
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SEED_PATH = Path(__file__).resolve().parents[1] / "src" / "kitchenpilot" / "seed" / "data" / "recipes_initial.json"
OUTPUT_DIR = Path(__file__).resolve().parent / "dataset"


def main() -> None:
    with SEED_PATH.open(encoding="utf-8") as f:
        recipes: list[dict[str, Any]] = json.load(f)

    single_turn: list[dict[str, Any]] = []
    multi_turn: list[dict[str, Any]] = []

    for recipe in recipes:
        rid = recipe["id"]
        name = recipe["name"]
        sources = recipe.get("source_urls", [])

        # --- beginner_tip question ---
        beginner_content = build_beginner_tip_content(recipe)
        if beginner_content:
            single_turn.append({
                "id": f"rag_{rid:03d}_01",
                "query": f"新手做{name}有什么关键技巧？",
                "category": "beginner_tip",
                "recipe_id": rid,
                "expected_recipes": [name],
                "expected_chunk_types": ["beginner_tip"],
                "must_include": extract_keywords(beginner_content, count=4),
                "risk_keywords": collect_risk_keywords(recipe),
                "source_urls": sources,
                "evidence_text": beginner_content,
            })

        # --- failure_reason question (use first failure with explanation) ---
        failures = recipe.get("common_failures", [])
        if failures:
            failure_text = failures[0]
            # Determine a natural query
            failure_query = make_failure_query(name, failure_text)
            single_turn.append({
                "id": f"rag_{rid:03d}_02",
                "query": failure_query,
                "category": "failure_reason",
                "recipe_id": rid,
                "expected_recipes": [name],
                "expected_chunk_types": ["failure_reason"],
                "must_include": extract_keywords(failure_text, count=4),
                "risk_keywords": collect_risk_keywords(recipe),
                "source_urls": sources,
                "evidence_text": failure_text,
            })

        # --- substitution or safety question ---
        subs = recipe.get("substitutions", {})
        safety = recipe.get("safety_notes", [])
        if subs:
            # Use first substitution
            original_ing = next(iter(subs))
            sub_text = subs[original_ing]
            single_turn.append({
                "id": f"rag_{rid:03d}_03",
                "query": f"做{name}没有{original_ing}怎么办？",
                "category": "substitution",
                "recipe_id": rid,
                "expected_recipes": [name],
                "expected_chunk_types": ["substitution"],
                "must_include": extract_keywords(sub_text, count=4),
                "risk_keywords": collect_risk_keywords(recipe),
                "source_urls": sources,
                "evidence_text": sub_text,
            })
        elif safety:
            safety_text = safety[0]
            single_turn.append({
                "id": f"rag_{rid:03d}_03",
                "query": f"做{name}有什么安全注意事项？",
                "category": "safety_note",
                "recipe_id": rid,
                "expected_recipes": [name],
                "expected_chunk_types": ["safety_note"],
                "must_include": extract_keywords(safety_text, count=4),
                "risk_keywords": collect_risk_keywords(recipe),
                "source_urls": sources,
                "evidence_text": safety_text,
            })

        # --- multi-turn question (failure follow-up) ---
        if failures:
            followup_text = failures[0]
            followup_query = make_failure_query(name, followup_text)
            multi_turn.append({
                "id": f"multi_{rid:03d}",
                "turns": [f"{name}怎么做？", followup_query],
                "expected_active_recipe": name,
                "expected_rewritten_query_contains": [name] + extract_keywords(followup_text, count=3),
                "expected_intent": "recipe_qa",
                "expected_chunk_types": ["failure_reason"],
                "must_include": extract_keywords(followup_text, count=4),
                "risk_keywords": collect_risk_keywords(recipe),
                "source_urls": sources,
                "category": "multi_turn_followup",
            })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    single_path = OUTPUT_DIR / "rag_questions.jsonl"
    multi_path = OUTPUT_DIR / "rag_multiturn_questions.jsonl"

    write_jsonl(single_path, single_turn)
    write_jsonl(multi_path, multi_turn)

    print(f"Single-turn: {len(single_turn)} questions → {single_path}")
    print(f"Multi-turn:  {len(multi_turn)} questions → {multi_path}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_beginner_tip_content(recipe: dict[str, Any]) -> str:
    """Build beginner tip content from step tips."""
    tips: list[str] = []
    for step in recipe.get("steps", []):
        tip = step.get("beginner_tip")
        if tip:
            tips.append(tip)
    if not tips:
        return ""
    # Combine the first 2-3 tips as the beginner content
    cleaned = [t.rstrip("。") for t in tips[:3]]
    return "。".join(cleaned) + "。"


def make_failure_query(recipe_name: str, failure_text: str) -> str:
    """Generate a natural question from a failure explanation."""
    # Try to extract the failure symptom from the text
    # Pattern: "XXX通常是..." → ask about the symptom
    symptom = extract_failure_symptom(failure_text, recipe_name)
    if symptom:
        return f"{recipe_name}为什么会{symptom}？"
    return f"{recipe_name}做失败了怎么办？"


def extract_failure_symptom(text: str, recipe_name: str = "") -> str:
    """Extract the failure symptom from an explanation."""
    # Pattern: "XXX通常是..." or "XXX多发生在..."
    match = re.match(r"^(.+?)(?:通常|多发生|常见|一般是)", text)
    if match:
        symptom = match.group(1).strip()
        return _strip_recipe_name(symptom, recipe_name)
    # Pattern: "XXX，通常是..."
    match = re.match(r"^(.+?)[，,]", text)
    if match:
        symptom = match.group(1).strip()
        return _strip_recipe_name(symptom, recipe_name)
    return ""


def _strip_recipe_name(symptom: str, recipe_name: str) -> str:
    """Remove recipe name prefix from symptom to avoid duplication in query."""
    if recipe_name and symptom.startswith(recipe_name):
        return symptom[len(recipe_name):].lstrip()
    return symptom


def extract_keywords(text: str, count: int = 4) -> list[str]:
    """Extract meaningful keyword fragments from text for must_include."""
    # Split text into meaningful phrases
    # Strategy: take overlapping windows of 4-6 characters
    if len(text) <= 6:
        return [text]

    keywords: list[str] = []
    # Try to get phrases at different positions
    step = max(2, len(text) // (count + 1))
    for i in range(0, len(text) - 3, step):
        end = min(i + 6, len(text))
        fragment = text[i:end].strip()
        if fragment and len(fragment) >= 2:
            keywords.append(fragment)
        if len(keywords) >= count:
            break

    # Ensure we have enough keywords
    if len(keywords) < count:
        # Add from beginning and end
        if text[:4] not in keywords:
            keywords.insert(0, text[:4])
        if text[-4:] not in keywords:
            keywords.append(text[-4:])

    return keywords[:count]


def collect_risk_keywords(recipe: dict[str, Any]) -> list[str]:
    """Collect risk-related keywords from ingredients and steps."""
    risks: list[str] = []
    ing_names = {item["ingredient"] for item in recipe.get("ingredients", [])}

    # Meat risks
    meat = {"鸡肉", "鸡翅", "猪肉", "牛肉", "五花肉", "排骨", "生肉"}
    if ing_names & meat:
        risks.append("生肉")

    # Seafood risks
    seafood = {"虾", "鱼", "罗氏虾", "海鲜"}
    if ing_names & seafood:
        risks.append("甲壳类")

    # Fish bone
    if any("鱼" in item["ingredient"] for item in recipe.get("ingredients", [])):
        risks.append("鱼刺")

    # Hot oil
    stir_fry = any(k in recipe["name"] for k in ["炒", "煎", "炸", "煸"])
    if stir_fry:
        risks.append("热油")

    # Raw bean
    if any("豆角" in item["ingredient"] or "四季豆" in item["ingredient"] for item in recipe.get("ingredients", [])):
        risks.append("未熟豆角")

    # Pressure cooker
    for step in recipe.get("steps", []):
        content = step.get("content", "") + (step.get("risk_tip") or "")
        if "高压锅" in content:
            risks.append("高压锅")

    return risks


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write rows as pretty-printed JSON, one object per blank-line-separated block."""
    with path.open("w", encoding="utf-8") as f:
        for i, row in enumerate(rows):
            if i > 0:
                f.write("\n")
            f.write(json.dumps(row, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
