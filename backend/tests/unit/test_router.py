from kitchenpilot.agent.nodes.intent_router import IntentClassification
from kitchenpilot.agent.router import IntentRouter
from kitchenpilot.core.llm import ChatMessage, ChatResult
from kitchenpilot.schemas.enums import IntentType
from kitchenpilot.services.mock_data import RECIPES


class _IntentProvider:
    """Fake provider used to test embedding and LLM routing without network calls."""

    def __init__(self, *, use_llm: bool = False) -> None:
        """Configure whether chat fallback should return a structured result."""
        self.use_llm = use_llm
        self.chat_calls = 0

    def chat(self, messages: list[ChatMessage]) -> ChatResult:
        """Return a structured LLM classification payload."""
        self.chat_calls += 1
        return ChatResult(
            content=(
                '{"intent":"daily_recommendation","confidence":0.77,'
                '"ingredients":[],"needs_clarification":false}'
            )
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return deterministic intent-like vectors for each input text."""
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        """Map text to a simple three-dimensional intent vector."""
        if self.use_llm:
            return [0.0, 0.0, 0.0]
        if any(term in text for term in ["番茄炒蛋", "怎么", "失败", "替代", "清蒸鱼"]):
            return [1.0, 0.0, 0.0]
        if any(term in text for term in ["我有", "食材", "冰箱", "米饭"]):
            return [0.0, 1.0, 0.0]
        if any(term in text for term in ["今天", "晚饭", "晚餐", "偏好"]):
            return [0.0, 0.0, 1.0]
        return [0.3, 0.3, 0.3]


def test_router_detects_ingredient_recommendation() -> None:
    """Verify ingredient recommendation can still be detected by rules."""
    router = IntentRouter(provider=_IntentProvider())

    intent = router.classify("我有鸡蛋、番茄和土豆，推荐一道简单菜。")

    assert intent == IntentType.INGREDIENT_RECOMMENDATION


def test_router_detects_recipe_qa() -> None:
    """Verify recipe questions can still be detected by rules."""
    router = IntentRouter(provider=_IntentProvider())

    intent = router.classify("土豆丝怎么炒得脆？")

    assert intent == IntentType.RECIPE_QA


def test_router_extracts_known_ingredients() -> None:
    """Verify the router extracts ingredients that exist in the local dataset."""
    router = IntentRouter(provider=_IntentProvider())
    ingredient = RECIPES[0].ingredients[0].ingredient

    ingredients = router.extract_ingredients(f"我有{ingredient}")

    assert ingredient in ingredients


def test_router_uses_embedding_confidence_for_non_rule_query() -> None:
    """Verify embedding similarity can classify a query when rules are weak."""
    router = IntentRouter(provider=_IntentProvider())

    result = router.classify_with_confidence("想按我的偏好安排一顿饭")

    assert isinstance(result, IntentClassification)
    assert result.intent == IntentType.DAILY_RECOMMENDATION
    assert result.confidence >= 0.80
    assert result.source == "embedding"


def test_router_falls_back_to_llm_when_confidence_is_low() -> None:
    """Verify low-confidence embedding results are handed to LLM classification."""
    provider = _IntentProvider(use_llm=True)
    router = IntentRouter(provider=provider)

    result = router.classify_with_confidence("清淡一点别太麻烦")

    assert result.intent == IntentType.DAILY_RECOMMENDATION
    assert result.source == "llm"
    assert provider.chat_calls == 1


def test_router_keeps_vague_non_cooking_query_as_unknown() -> None:
    """Verify vague non-cooking requests are clarified instead of over-routed."""
    provider = _IntentProvider(use_llm=True)
    router = IntentRouter(provider=provider)

    result = router.classify_with_confidence("随便帮我想想")

    assert result.intent == IntentType.UNKNOWN
    assert result.needs_clarification
    assert "根据已有食材推荐菜" in result.clarification_question
