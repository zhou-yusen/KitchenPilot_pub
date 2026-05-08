from kitchenpilot.schemas.recipe import Recipe
from kitchenpilot.services.mock_data import RECIPES


class RecipeService:
    def list_recipes(self) -> list[Recipe]:
        return RECIPES

    def get_recipe(self, recipe_id: int) -> Recipe | None:
        return next((recipe for recipe in RECIPES if recipe.id == recipe_id), None)

    def find_by_name(self, query: str) -> Recipe | None:
        return next((recipe for recipe in RECIPES if recipe.name in query), None)

    def find_by_ingredients(self, ingredients: list[str]) -> list[Recipe]:
        normalized = set(ingredients)
        candidates: list[Recipe] = []
        for recipe in RECIPES:
            recipe_ingredients = {item.ingredient for item in recipe.ingredients}
            if normalized & recipe_ingredients:
                candidates.append(recipe)
        return candidates

