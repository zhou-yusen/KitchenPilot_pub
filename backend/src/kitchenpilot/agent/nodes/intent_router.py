from kitchenpilot.agent.state import AgentState
from kitchenpilot.schemas.enums import IntentType
from kitchenpilot.services.mock_data import RECIPES
from kitchenpilot.services.user_memory_service import UserMemoryService


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


router = IntentRouter()
user_memory_service = UserMemoryService()


def _trace(state: AgentState, event: str) -> list[str]:
    return [*state.get("execution_trace", []), event]


def parse_input_node(state: AgentState) -> AgentState:
    query = state["query"]
    existing = state.get("user_ingredients", [])
    extracted = router.extract_ingredients(query)
    merged = sorted(set(existing) | set(extracted))
    return {
        **state,
        "user_ingredients": merged,
        "execution_trace": _trace(state, f"解析输入，识别食材：{merged or '无'}"),
    }


def load_user_history_node(state: AgentState) -> AgentState:
    profile = user_memory_service.get_user_profile(state.get("user_id", "demo_user"))
    return {
        **state,
        "user_profile": profile,
        "execution_trace": _trace(state, "加载用户历史和偏好"),
    }


def route_intent_node(state: AgentState) -> AgentState:
    intent = router.classify(state["query"], state.get("user_ingredients", []))
    return {
        **state,
        "intent": intent,
        "execution_trace": _trace(state, f"Router 识别意图：{intent}"),
    }


def route_after_intent(state: AgentState) -> str:
    intent = state.get("intent", IntentType.UNKNOWN)
    if intent == IntentType.RECIPE_QA:
        return "recipe_qa"
    if intent == IntentType.INGREDIENT_RECOMMENDATION:
        return "ingredient_recommendation"
    if intent == IntentType.DAILY_RECOMMENDATION:
        return "daily_recommendation"
    return "unknown"


__all__ = [
    "IntentRouter",
    "_trace",
    "load_user_history_node",
    "parse_input_node",
    "route_after_intent",
    "route_intent_node",
]
