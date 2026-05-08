from kitchenpilot.agent.nodes.intent_router import _trace
from kitchenpilot.agent.state import AgentState
from kitchenpilot.recommender.service import RecommendationService


recommendation_service = RecommendationService()


def ingredient_recommendation_node(state: AgentState) -> AgentState:
    """Generate recommendations from ingredients stored in state."""
    recommendations = recommendation_service.recommend_by_ingredients(
        user_id=state.get("user_id", "demo_user"),
        ingredients=state.get("user_ingredients", []),
    )
    answer = _format_recommendation_answer("根据你已有的食材，推荐如下：", recommendations)
    return {
        **state,
        "recommendations": recommendations,
        "draft_answer": answer,
        "execution_trace": _trace(state, f"执行食材推荐，生成 {len(recommendations)} 个候选"),
    }


def daily_recommendation_node(state: AgentState) -> AgentState:
    """Generate daily recommendations from the user profile."""
    recommendations = recommendation_service.daily_recommend(state.get("user_id", "demo_user"))
    answer = _format_recommendation_answer("结合你的历史偏好，今日推荐如下：", recommendations)
    return {
        **state,
        "recommendations": recommendations,
        "draft_answer": answer,
        "execution_trace": _trace(state, f"执行每日推荐，生成 {len(recommendations)} 个候选"),
    }


def unknown_intent_node(state: AgentState) -> AgentState:
    """Return a clarification question for an unclassified query."""
    answer = state.get("clarification_question", "")
    if not answer:
        answer = (
            "我暂时无法判断你的具体需求。\n"
            "你是想让我：\n"
            "1. 根据已有食材推荐菜？\n"
            "2. 按你的偏好推荐今天吃什么？\n"
            "3. 回答某道菜的具体做法？"
        )
    return {
        **state,
        "needs_clarification": True,
        "clarification_question": answer,
        "draft_answer": answer,
        "execution_trace": _trace(state, "进入未知意图澄清节点"),
    }


def _format_recommendation_answer(prefix: str, recommendations) -> str:
    """Format recommendation results into user-facing text."""
    if not recommendations:
        return "暂时没有找到足够匹配的菜谱。可以补充更多食材，或降低难度、耗时要求。"

    lines = [prefix]
    for index, item in enumerate(recommendations, start=1):
        reasons = "；".join(item.reasons)
        missing = "、".join(item.missing_ingredients) if item.missing_ingredients else "无"
        lines.append(
            f"{index}. {item.recipe_name}：难度 {item.difficulty}，约 {item.time_minutes} 分钟。"
            f"缺少食材：{missing}。推荐理由：{reasons}。"
        )
    return "\n".join(lines)


__all__ = [
    "daily_recommendation_node",
    "ingredient_recommendation_node",
    "unknown_intent_node",
]
