from kitchenpilot.schemas.enums import IntentType
from kitchenpilot.services.safety_check_service import SafetyCheckService


def test_recipe_qa_without_sources_needs_repair() -> None:
    """验证菜谱问答缺少来源时，质量检查会要求修复答案。"""
    service = SafetyCheckService()

    result = service.check(
        intent=IntentType.RECIPE_QA,
        answer="可以这样做。",
        sources=[],
        recommendations=[],
        user_ingredients=[],
    )

    assert not result.passed
    assert result.needs_repair


def test_dangerous_phrase_is_rejected() -> None:
    """验证包含危险烹饪建议的答案会被安全检查拦截。"""
    service = SafetyCheckService()

    result = service.check(
        intent=IntentType.FALLBACK,
        answer="生鸡肉直接吃也可以。",
        sources=[],
        recommendations=[],
        user_ingredients=[],
    )

    assert not result.passed
