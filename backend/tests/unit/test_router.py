from kitchenpilot.agent.router import IntentRouter
from kitchenpilot.schemas.enums import IntentType


def test_router_detects_ingredient_recommendation() -> None:
    router = IntentRouter()

    intent = router.classify("我家里有鸡蛋、番茄、土豆，推荐一道简单菜。")

    assert intent == IntentType.INGREDIENT_RECOMMENDATION


def test_router_detects_recipe_qa() -> None:
    router = IntentRouter()

    intent = router.classify("土豆丝怎么炒得脆？")

    assert intent == IntentType.RECIPE_QA


def test_router_extracts_known_ingredients() -> None:
    router = IntentRouter()

    ingredients = router.extract_ingredients("我有鸡蛋和土豆")

    assert "鸡蛋" in ingredients
    assert "土豆" in ingredients

