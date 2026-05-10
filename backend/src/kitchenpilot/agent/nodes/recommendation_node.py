from kitchenpilot.agent.nodes.intent_router import _trace
from kitchenpilot.agent.state import AgentState
from kitchenpilot.recommender.service import RecommendationService
from kitchenpilot.schemas.enums import RecommendationType

recommendation_service = RecommendationService()


def recommendation_node(state: AgentState) -> AgentState:
    """Generate recommendations from the unified recommendation state."""
    recommendation_type = state.get("recommendation_type") or RecommendationType.INGREDIENTS
    recommendations = recommendation_service.recommend(
        user_id=state.get("user_id", "demo_user"),
        recommendation_type=recommendation_type,
        ingredients=state.get("user_ingredients", []),
    )
    answer = _format_recommendation_answer(
        _recommendation_prefix(recommendation_type),
        recommendations,
        recommendation_type,
    )
    return {
        **state,
        "recommendation_type": recommendation_type,
        "recommendations": recommendations,
        "draft_answer": answer,
        "execution_trace": _trace(
            state,
            f"执行推荐：{recommendation_type}，生成 {len(recommendations)} 个候选",
        ),
    }


def fallback_node(state: AgentState) -> AgentState:
    """Return a clarification question for an unclassified query."""
    answer = state.get("clarification_question", "")
    if not answer:
        answer = (
            "我暂时无法判断你的具体需求。\n"
            "你可以这样问：\n"
            "1. 我有鸡蛋和土豆，推荐一道菜。\n"
            "2. 今天吃什么？\n"
            "3. 土豆丝怎么炒得脆？"
        )
    return {
        **state,
        "needs_clarification": True,
        "clarification_question": answer,
        "draft_answer": answer,
        "execution_trace": _trace(state, "进入 fallback 澄清节点"),
    }


def _recommendation_prefix(recommendation_type: RecommendationType) -> str:
    """Return the user-facing prefix for a recommendation subtype."""
    if recommendation_type == RecommendationType.DAILY:
        return "结合你的历史偏好，今日推荐如下："
    return "根据你已有的食材，推荐如下："


def _format_recommendation_answer(
    prefix: str,
    recommendations,
    recommendation_type: RecommendationType,
) -> str:
    """Format recommendation results into user-facing text."""
    if not recommendations:
        return "暂时没有找到足够匹配的菜谱。可以补充更多食材，或降低难度、耗时要求。"

    lines = [prefix]
    for index, item in enumerate(recommendations, start=1):
        reasons = "；".join(item.reasons)
        missing = "、".join(item.missing_ingredients) if item.missing_ingredients else "无"
        missing_label = (
            "需准备食材"
            if recommendation_type == RecommendationType.DAILY
            else "缺少食材"
        )
        lines.append(
            f"{index}. {item.recipe_name}：难度 {item.difficulty}，约 {item.time_minutes} 分钟。"
            f"{missing_label}：{missing}。推荐理由：{reasons}。"
        )
    return "\n".join(lines)


__all__ = [
    "fallback_node",
    "recommendation_node",
]
