import json
from pathlib import Path
from typing import Any

from kitchenpilot.schemas.recipe import Recipe


DEFAULT_RECIPE_DATA_PATH = Path(__file__).with_name("data") / "recipes_initial.json"


def load_recipe_dataset_entries(path: Path | str = DEFAULT_RECIPE_DATA_PATH) -> list[dict[str, Any]]:
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
        entries.append(item)

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
