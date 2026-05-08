from kitchenpilot.schemas.enums import IntentType
from kitchenpilot.schemas.quality import QualityCheckResult
from kitchenpilot.schemas.recipe import SourceChunk
from kitchenpilot.schemas.recommendation import RecommendationResult


class SafetyCheckService:
    dangerous_phrases = [
        "不用加热",
        "半生",
        "变质",
        "发霉",
        "生鸡肉直接吃",
        "不用洗手",
    ]
    high_risk_terms = ["鸡翅", "鸡肉", "禽肉", "五花肉", "肉类", "海鲜"]

    def check(
        self,
        *,
        intent: IntentType,
        answer: str,
        sources: list[SourceChunk],
        recommendations: list[RecommendationResult],
        user_ingredients: list[str],
    ) -> QualityCheckResult:
        issues: list[str] = []
        safety_warnings: list[str] = []

        if intent == IntentType.RECIPE_QA and not sources:
            issues.append("RAG 问答缺少知识库引用来源。")

        if recommendations and user_ingredients:
            has_any_match = any(item.matched_ingredients for item in recommendations)
            if not has_any_match:
                issues.append("推荐结果没有匹配用户已有食材。")

        if any(phrase in answer for phrase in self.dangerous_phrases):
            issues.append("回答中存在潜在危险或不可靠烹饪建议。")

        if any(term in answer for term in self.high_risk_terms) and "熟" not in answer:
            safety_warnings.append("涉及肉类、禽类或海鲜时，需要提醒充分加热。")

        passed = not issues
        return QualityCheckResult(
            passed=passed,
            issues=issues,
            safety_warnings=safety_warnings,
            needs_repair=not passed or bool(safety_warnings),
        )
