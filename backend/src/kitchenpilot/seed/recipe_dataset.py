import json
import re
from pathlib import Path
from typing import Any

from kitchenpilot.schemas.recipe import Recipe

DATA_DIR = Path(__file__).with_name("data")
DEFAULT_RECIPE_DATA_PATH = DATA_DIR / "recipes_extracted.json"


def load_recipe_dataset_entries(
    path: Path | str = DEFAULT_RECIPE_DATA_PATH,
) -> list[dict[str, Any]]:
    """Load raw recipe dictionaries from the seed JSON file and run dataset-level checks."""
    data_path = Path(path)
    with data_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"Recipe dataset must be a list: {data_path}")

    entries: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Recipe dataset item #{index} must be an object")
        entries.append(_normalize_entry(item))

    _validate_unique_keys(entries)
    _validate_step_orders(entries)
    return entries


def load_recipes(path: Path | str = DEFAULT_RECIPE_DATA_PATH) -> list[Recipe]:
    """Load the seed JSON file and convert every entry into the public Recipe schema."""
    return [Recipe.model_validate(entry) for entry in load_recipe_dataset_entries(path)]


def _validate_unique_keys(entries: list[dict[str, Any]]) -> None:
    """Ensure recipe IDs and names are unique before the data is inserted into SQLite."""
    seen_ids: set[int] = set()
    seen_names: set[str] = set()
    for entry in entries:
        recipe_id = entry.get("id")
        name = entry.get("name")
        if not isinstance(recipe_id, int):
            raise ValueError(f"Recipe id must be an integer: {recipe_id!r}")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Recipe name must be a non-empty string: {name!r}")
        if recipe_id in seen_ids:
            raise ValueError(f"Duplicate recipe id: {recipe_id}")
        if name in seen_names:
            raise ValueError(f"Duplicate recipe name: {name}")
        seen_ids.add(recipe_id)
        seen_names.add(name)


def _validate_step_orders(entries: list[dict[str, Any]]) -> None:
    """Ensure every recipe has contiguous step orders starting at 1."""
    for entry in entries:
        steps = entry.get("steps", [])
        if not isinstance(steps, list) or not steps:
            raise ValueError(f"Recipe must include at least one step: {entry.get('name')}")

        expected_orders = list(range(1, len(steps) + 1))
        actual_orders = [step.get("order") for step in steps if isinstance(step, dict)]
        if actual_orders != expected_orders:
            raise ValueError(
                f"Recipe steps must be ordered from 1 without gaps: {entry.get('name')}"
            )


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Return the runtime recipe shape for normalized or extracted seed records."""
    if "id" in entry and "name" in entry:
        return entry
    if "recipe_id" in entry and "recipe_name" in entry:
        return _normalize_extracted_entry(entry)
    raise ValueError(f"Unsupported recipe dataset entry keys: {sorted(entry)}")


def _normalize_extracted_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Convert a fixed eval extraction record into the runtime Recipe schema."""
    difficulty = str(entry.get("difficulty") or "easy")
    chunks = [
        chunk
        for chunk in entry.get("chunks", [])
        if isinstance(chunk, dict) and chunk.get("content")
    ]
    return {
        "id": int(entry["recipe_id"]),
        "name": str(entry["recipe_name"]),
        "description": str(entry.get("intro") or ""),
        "difficulty": difficulty,
        "time_minutes": _time_minutes(str(entry.get("time") or "")),
        "beginner_friendly": difficulty != "hard",
        "cuisine": "家常菜",
        "seasons": [],
        "ingredients": _ingredients(str(entry.get("ingredients") or "")),
        "steps": _steps(entry.get("steps", [])),
        "common_failures": [
            *[str(item) for item in entry.get("failures", []) if str(item).strip()],
            *_chunk_contents(chunks, "failure_reason"),
        ],
        "substitutions": {
            _substitution_key(content, index): content
            for index, content in enumerate(_chunk_contents(chunks, "substitution"), start=1)
        },
        "safety_notes": _chunk_contents(chunks, "safety_note"),
        "source_urls": [str(item) for item in entry.get("sources", []) if str(item).strip()],
    }


def _time_minutes(value: str) -> int:
    """Extract the first minute count from text such as '15 分钟'."""
    match = re.search(r"\d+", value)
    if not match:
        raise ValueError(f"Recipe time must include minutes: {value!r}")
    return int(match.group())


def _ingredients(value: str) -> list[dict[str, object]]:
    """Split extracted ingredient text into runtime ingredient dictionaries."""
    ingredients: list[dict[str, object]] = []
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        name, separator, amount = item.partition(" ")
        ingredients.append(
            {
                "ingredient": name,
                "amount": amount.strip() if separator else "",
                "required": True,
            }
        )
    if not ingredients:
        raise ValueError("Extracted recipe must include ingredients.")
    return ingredients


def _steps(values: object) -> list[dict[str, object]]:
    """Parse extracted step text and inline tip/risk markers."""
    if not isinstance(values, list):
        raise ValueError("Extracted recipe steps must be a list.")
    steps: list[dict[str, object]] = []
    for order, raw_step in enumerate(values, start=1):
        value = str(raw_step).strip()
        steps.append(
            {
                "order": order,
                "content": re.sub(r"\s*\[(提示|风险)：.*?\]", "", value).strip(),
                "beginner_tip": _marker(value, "提示"),
                "risk_tip": _marker(value, "风险"),
            }
        )
    return steps


def _marker(value: str, label: str) -> str | None:
    """Return one inline extraction marker such as '[提示：...]'."""
    match = re.search(rf"\[{label}：(.*?)\]", value)
    return match.group(1).strip() if match else None


def _chunk_contents(chunks: list[dict[str, Any]], chunk_type: str) -> list[str]:
    """Return chunk texts for one extracted chunk type."""
    return [
        str(chunk["content"]).strip()
        for chunk in chunks
        if chunk.get("chunk_type") == chunk_type and str(chunk["content"]).strip()
    ]


def _substitution_key(content: str, index: int) -> str:
    """Derive a readable key for substitution notes when extraction lacks a slot field."""
    match = re.match(r"(?:没有|不想放)(.+?)(?:时|，)", content)
    if match:
        return match.group(1)
    return f"替代建议 {index}"
