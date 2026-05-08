from kitchenpilot.schemas.enums import IntentType
from kitchenpilot.services.mock_data import RECIPES


class IntentRouter:
    def classify(self, query: str, ingredients: list[str] | None = None) -> IntentType:
        ingredients = ingredients or []
        if self._is_daily_recommendation(query):
            return IntentType.DAILY_RECOMMENDATION
        if self._is_recipe_qa(query):
            return IntentType.RECIPE_QA
        if ingredients or self._is_ingredient_recommendation(query):
            return IntentType.INGREDIENT_RECOMMENDATION
        return IntentType.UNKNOWN

    def extract_ingredients(self, query: str) -> list[str]:
        known = {
            item.ingredient
            for recipe in RECIPES
            for item in recipe.ingredients
            if len(item.ingredient) >= 1
        }
        return sorted({ingredient for ingredient in known if ingredient in query})

    @staticmethod
    def _is_daily_recommendation(query: str) -> bool:
        daily_terms = ["今日推荐", "今天推荐", "每日推荐", "给我推荐今天", "今天吃什么"]
        return any(term in query for term in daily_terms)

    @staticmethod
    def _is_ingredient_recommendation(query: str) -> bool:
        ingredient_terms = ["我有", "家里有", "已有", "食材", "推荐一道", "能做什么"]
        return any(term in query for term in ingredient_terms)

    @staticmethod
    def _is_recipe_qa(query: str) -> bool:
        qa_terms = ["怎么", "如何", "为什么", "注意", "替代", "失败", "太甜", "做法"]
        recipe_names = [recipe.name for recipe in RECIPES]
        return any(term in query for term in qa_terms) or any(
            name in query for name in recipe_names
        )
