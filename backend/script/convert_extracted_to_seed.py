"""Convert recipes_extracted.json into the full recipes_initial.json seed format.

Reads the extracted JSON (with chunks), enriches missing fields, and writes
the output in the exact schema expected by kitchenpilot.seed.recipe_dataset.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

EVAL_DIR = Path(__file__).resolve().parents[1] / "evals" / "dataset"
SEED_DIR = Path(__file__).resolve().parents[1] / "src" / "kitchenpilot" / "seed" / "data"

EXTRACTED_PATH = EVAL_DIR / "recipes_extracted.json"
OUTPUT_PATH = SEED_DIR / "recipes_initial.json"

SEASONS_ALL = ["spring", "summer", "autumn", "winter"]


def main() -> None:
    with EXTRACTED_PATH.open(encoding="utf-8") as f:
        extracted: list[dict[str, Any]] = json.load(f)

    recipes: list[dict[str, Any]] = []
    for entry in extracted:
        recipes.append(convert_entry(entry))

    SEED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(recipes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(recipes)} recipes to {OUTPUT_PATH}")


def convert_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Convert one extracted entry into the full seed schema."""
    recipe_id = entry["recipe_id"]
    name = entry["recipe_name"]

    # Parse chunks by type
    chunks_by_type: dict[str, list[str]] = {}
    for chunk in entry.get("chunks", []):
        chunks_by_type.setdefault(chunk["chunk_type"], []).append(chunk["content"])

    # Parse ingredients string → structured list
    ingredients = parse_ingredients(entry.get("ingredients", ""))

    # Parse steps strings → structured steps with tips
    steps = parse_steps(entry.get("steps", []))

    # Enrich common_failures
    failures = entry.get("failures", [])
    failure_reason_chunk = (chunks_by_type.get("failure_reason") or [""])[0]
    common_failures = build_common_failures(name, failures, failure_reason_chunk, ingredients)

    # Enrich substitutions
    substitution_chunk = (chunks_by_type.get("substitution") or [""])[0]
    substitutions = build_substitutions(name, ingredients, substitution_chunk)

    # Enrich safety_notes
    safety_chunk = (chunks_by_type.get("safety_note") or [""])[0]
    safety_notes = build_safety_notes(name, ingredients, steps, safety_chunk)

    # Infer metadata
    difficulty = entry.get("difficulty", "easy")
    time_minutes = parse_time(entry.get("time", "15 分钟"))
    beginner_friendly = difficulty in ("easy", "medium")
    seasons = infer_seasons(name, ingredients)

    return {
        "id": recipe_id,
        "name": name,
        "description": entry.get("intro", ""),
        "difficulty": difficulty,
        "time_minutes": time_minutes,
        "beginner_friendly": beginner_friendly,
        "cuisine": "家常菜",
        "seasons": seasons,
        "ingredients": ingredients,
        "steps": steps,
        "common_failures": common_failures,
        "substitutions": substitutions,
        "safety_notes": safety_notes,
        "source_urls": entry.get("sources", []),
    }


# ---------------------------------------------------------------------------
# Ingredient parsing
# ---------------------------------------------------------------------------

def parse_ingredients(raw: str) -> list[dict[str, Any]]:
    """Parse '番茄 2个, 鸡蛋 3个, ...' into structured ingredient list."""
    result: list[dict[str, Any]] = []
    if not raw:
        return result
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        match = re.match(r"^(.+?)\s+(.+)$", item)
        if match:
            name, amount = match.group(1).strip(), match.group(2).strip()
        else:
            name, amount = item, ""
        required = not any(k in name or k in amount for k in ["少量", "适量", "可选", "按需"])
        result.append({"ingredient": name, "amount": amount, "required": required})
    return result


# ---------------------------------------------------------------------------
# Step parsing
# ---------------------------------------------------------------------------

def parse_steps(raw_steps: list[str]) -> list[dict[str, Any]]:
    """Parse step strings with embedded [提示：...] [风险：...] into structured steps."""
    result: list[dict[str, Any]] = []
    for i, step_text in enumerate(raw_steps, start=1):
        beginner_tip = None
        risk_tip = None

        # Extract [风险：...] (do this first, before [提示：...])
        risk_match = re.search(r"\[风险[：:](.+?)\]", step_text)
        if risk_match:
            risk_tip = risk_match.group(1).strip()
            step_text = step_text[: risk_match.start()] + step_text[risk_match.end() :]
            step_text = step_text.strip()

        # Extract [提示：...]
        tip_match = re.search(r"\[提示[：:](.+?)\]", step_text)
        if tip_match:
            beginner_tip = tip_match.group(1).strip()
            step_text = step_text[: tip_match.start()] + step_text[tip_match.end() :]
            step_text = step_text.strip()

        # Clean up remaining brackets
        step_text = re.sub(r"\s+", " ", step_text).strip()

        result.append({
            "order": i,
            "content": step_text,
            "beginner_tip": beginner_tip,
            "risk_tip": risk_tip,
        })
    return result


# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------

def parse_time(raw: str) -> int:
    """Parse '15 分钟' → 15."""
    match = re.search(r"(\d+)", raw)
    return int(match.group(1)) if match else 15


# ---------------------------------------------------------------------------
# Season inference
# ---------------------------------------------------------------------------

def infer_seasons(name: str, ingredients: list[dict[str, Any]]) -> list[str]:
    """Return seasonal tags based on recipe name and ingredients."""
    names = [item["ingredient"] for item in ingredients]
    winter = any(k in name or any(k in n for n in names) for k in ["萝卜", "白菜", "冬瓜", "排骨汤", "炖"])
    summer = any(k in name or any(k in n for n in names) for k in ["黄瓜", "凉拌", "藕", "虾"])
    if winter and not summer:
        return ["autumn", "winter"]
    if summer and not winter:
        return ["spring", "summer"]
    return SEASONS_ALL


# ---------------------------------------------------------------------------
# Failure enrichment
# ---------------------------------------------------------------------------

def build_common_failures(
    recipe_name: str,
    failures: list[str],
    failure_chunk: str,
    ingredients: list[dict[str, Any]],
) -> list[str]:
    """Expand brief failure titles into detailed explanations."""
    result: list[str] = []
    ing_names = [item["ingredient"] for item in ingredients]

    for i, title in enumerate(failures):
        if i == 0 and failure_chunk:
            # Use the existing chunk content for the first failure
            result.append(failure_chunk)
        else:
            result.append(generate_failure_explanation(recipe_name, title, ing_names))
    return result


def generate_failure_explanation(recipe_name: str, title: str, ingredients: list[str]) -> str:
    """Generate a plausible failure explanation based on context."""
    # Common patterns
    patterns = {
        "不出汁": f"{recipe_name}不出汁通常是食材没有充分翻炒软化，或火力不够导致水分无法释放。",
        "发粘": f"{recipe_name}发粘通常是淀粉没有冲洗干净，或炒制时间过长导致食材出水。",
        "太老": f"{recipe_name}变老通常是加热时间过长，或第一次炒制后没有及时盛出。",
        "太柴": f"{recipe_name}发柴通常是腌制不足、切得太厚，或滑炒时间过长。",
        "太油": f"{recipe_name}太油通常是油量过多或没有控油，可以减少用油量或出锅前沥油。",
        "发苦": f"{recipe_name}发苦通常是调料炒制过度，或糖色/酱油加热过久。",
        "夹生": f"{recipe_name}夹生通常是火太大或食材切得太大块，导致外熟内生。",
        "太咸": f"{recipe_name}太咸通常是盐或酱油放多了，可以减少用量或出锅前再调味。",
        "太甜": f"{recipe_name}太甜通常是糖放多了，可以减少用量或用少量醋平衡甜味。",
        "糊锅": f"{recipe_name}糊锅通常是火力太大或没有及时翻动，尤其是含糖分的菜。",
        "散": f"{recipe_name}散通常是翻炒太用力或食材没有提前定型，应轻推轻翻。",
        "碎": f"{recipe_name}碎通常是翻炒太频繁或食材含水量大，应减少翻动次数。",
        "不入味": f"{recipe_name}不入味通常是腌制时间不足或调味料没有提前拌匀。",
        "不熟": f"{recipe_name}内部不熟通常是加热时间不足或食材太大块，应确保充分加热。",
        "不软": f"{recipe_name}不软通常是炖煮时间不足，应延长炖煮时间或提前浸泡。",
        "发黑": f"{recipe_name}发黑通常是食材氧化或与铁锅反应，可以提前泡水或缩短烹饪时间。",
        "出水多": f"{recipe_name}出水多通常是盐放太早或火力不足，可以后放盐并用大火快炒。",
        "腥味": f"{recipe_name}腥味重通常是去腥处理不充分，可以用葱姜料酒提前腌制或焯水。",
        "颜色发黄": f"{recipe_name}颜色发黄通常是加热时间过长，可以缩短烹饪时间。",
        "酸甜比例": f"{recipe_name}酸甜比例失衡通常是调味汁比例不稳定，建议提前调好碗汁。",
        "焦": f"{recipe_name}焦通常是火力太大或加热时间过长，应控制火候并及时出锅。",
        "结块": f"{recipe_name}结块通常是食材水分过多或没有提前打散处理。",
        "干硬": f"{recipe_name}干硬通常是烹饪时间过长或水分不足，可以缩短时间或增加汤汁。",
    }

    for keyword, explanation in patterns.items():
        if keyword in title:
            return explanation

    # Fallback: generic explanation
    return f"{recipe_name}{title}，通常是火候或操作细节没有控制好，建议按步骤严格操作。"


# ---------------------------------------------------------------------------
# Substitution enrichment
# ---------------------------------------------------------------------------

def build_substitutions(
    recipe_name: str,
    ingredients: list[dict[str, Any]],
    substitution_chunk: str,
) -> dict[str, str]:
    """Build substitutions dict from existing chunk and inferred alternatives."""
    result: dict[str, str] = {}

    # Parse existing substitution chunk if present
    if substitution_chunk:
        result = parse_substitution_chunk(substitution_chunk)

    # Generate missing common substitutions based on ingredients
    ing_names = [item["ingredient"] for item in ingredients]
    auto_subs = generate_common_substitutions(recipe_name, ing_names)
    for original, replacement in auto_subs.items():
        if original not in result:
            result[original] = replacement

    return result


def parse_substitution_chunk(chunk: str) -> dict[str, str]:
    """Parse '不想放糖时，可以选更成熟的番茄，...' into {ingredient: explanation}."""
    result: dict[str, str] = {}
    if not chunk:
        return result

    # Try to extract original ingredient and replacement
    # Pattern: "没有X时..." or "不想放X时..."
    match = re.search(r"(?:没有|不想放|不放)(.+?)(?:时|可以|，|。)", chunk)
    if match:
        ingredient = match.group(1).strip()
        result[ingredient] = chunk
    else:
        # Use the whole chunk as a generic substitution
        result["替代方案"] = chunk
    return result


def generate_common_substitutions(recipe_name: str, ingredients: list[str]) -> dict[str, str]:
    """Generate reasonable substitutions for common ingredients."""
    subs: dict[str, str] = {}
    common = {
        "蚝油": "没有蚝油时可用生抽、少量糖和蒜末做简化酱汁。",
        "豆瓣酱": "没有豆瓣酱时可用辣椒粉、花椒和少量酱油替代，但风味会明显不同。",
        "料酒": "没有料酒时可用少量白酒或黄酒替代。",
        "生抽": "没有生抽时可用普通酱油替代，用量减半。",
        "老抽": "没有老抽时可省略，颜色会浅一些。",
        "白糖": "不想放糖时可用少量蜂蜜替代。",
        "醋": "没有指定醋时可用米醋或白醋替代，酸香会有区别。",
        "泡椒": "没有泡椒时可用豆瓣酱和少量醋糖替代。",
        "花椒": "没有花椒时可用花椒油替代。",
        "蒜苗": "没有蒜苗时可用青椒、洋葱或青蒜替代。",
        "花生": "没有花生可以用腰果替代，也可以不放。",
        "蚝油": "没有蚝油时可用生抽、少量糖和蒜末做简化酱汁。",
        "虾皮": "没有虾皮时可以只用紫菜、鸡蛋和葱花，也可以加少量鸡精。",
        "干辣椒": "没有干辣椒时可以只用蒜片和少量醋调味。",
    }
    for ing in ingredients:
        if ing in common:
            subs[ing] = common[ing]
    return subs


# ---------------------------------------------------------------------------
# Safety note enrichment
# ---------------------------------------------------------------------------

def build_safety_notes(
    recipe_name: str,
    ingredients: list[dict[str, Any]],
    steps: list[dict[str, Any]],
    safety_chunk: str,
) -> list[str]:
    """Build safety notes from existing chunk and recipe context."""
    result: list[str] = []
    ing_names = [item["ingredient"] for item in ingredients]

    # Use existing chunk content
    if safety_chunk:
        result.append(safety_chunk)

    # Extract risk tips from steps
    for step in steps:
        if step.get("risk_tip"):
            result.append(step["risk_tip"])

    # Generate common safety notes based on ingredients
    auto_notes = generate_common_safety_notes(recipe_name, ing_names)
    for note in auto_notes:
        if note not in result:
            result.append(note)

    return result


def generate_common_safety_notes(recipe_name: str, ingredients: list[str]) -> list[str]:
    """Generate safety notes based on ingredient types."""
    notes: list[str] = []
    ing_set = set(ingredients)

    meat_ingredients = {"鸡肉", "鸡翅", "鸡翅中", "猪肉", "牛肉", "五花肉", "排骨", "里脊肉"}
    seafood_ingredients = {"虾", "鱼", "罗氏虾", "白灼虾"}
    allergen_ingredients = {"虾", "罗氏虾", "鸡蛋"}

    if ing_set & meat_ingredients:
        notes.append(f"{recipe_name}涉及肉类食材，必须确保充分加热至完全熟透。")
    if ing_set & seafood_ingredients:
        notes.append(f"{recipe_name}涉及海鲜食材，需确认无过敏史，并确保完全熟透。")
    if ing_set & allergen_ingredients:
        notes.append(f"烹饪前需提示过敏风险（鸡蛋、甲壳类等）。")

    # Hot oil warning for stir-fry
    stir_fry = any(k in recipe_name for k in ["炒", "煎", "炸", "煸"])
    if stir_fry:
        notes.append("下锅前确保食材表面干燥，避免热油飞溅。")

    return notes


if __name__ == "__main__":
    main()
