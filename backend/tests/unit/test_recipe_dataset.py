from kitchenpilot.seed.recipe_dataset import DEFAULT_RECIPE_DATA_PATH, load_recipes


def test_extracted_recipe_dataset_loads_runtime_seed_schema() -> None:
    """Verify the 50-recipe HTML extraction matches the runtime Recipe schema."""
    recipes = load_recipes(DEFAULT_RECIPE_DATA_PATH)

    first = recipes[0]
    assert len(recipes) == 50
    assert first.id == 1
    assert first.name == "番茄炒蛋"
    assert first.time_minutes == 15
    assert first.ingredients[0].ingredient == "番茄"
    assert first.steps[2].beginner_tip
    assert first.steps[2].risk_tip
    assert first.common_failures
    assert first.substitutions
