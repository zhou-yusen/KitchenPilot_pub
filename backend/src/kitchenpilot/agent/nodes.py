from kitchenpilot.agent.router import IntentRouter
from kitchenpilot.rag.service import RAGService
from kitchenpilot.recommender.service import RecommendationService
from kitchenpilot.schemas.agent import AgentState
from kitchenpilot.schemas.enums import IntentType
from kitchenpilot.schemas.quality import QualityCheckResult
from kitchenpilot.services.safety_check_service import SafetyCheckService
from kitchenpilot.services.user_memory_service import UserMemoryService


router = IntentRouter()
rag_service = RAGService()
recommendation_service = RecommendationService()
user_memory_service = UserMemoryService()
safety_check_service = SafetyCheckService()


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


def recipe_qa_node(state: AgentState) -> AgentState:
    result = rag_service.answer(state["query"])
    return {
        **state,
        "retrieved_context": result.sources,
        "draft_answer": result.answer,
        "execution_trace": _trace(state, f"执行菜谱问答 RAG，命中 {len(result.sources)} 条来源"),
    }


def ingredient_recommendation_node(state: AgentState) -> AgentState:
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
    recommendations = recommendation_service.daily_recommend(state.get("user_id", "demo_user"))
    answer = _format_recommendation_answer("结合你的历史偏好，今日推荐如下：", recommendations)
    return {
        **state,
        "recommendations": recommendations,
        "draft_answer": answer,
        "execution_trace": _trace(state, f"执行每日推荐，生成 {len(recommendations)} 个候选"),
    }


def unknown_intent_node(state: AgentState) -> AgentState:
    answer = "我暂时无法判断你的具体需求。可以问具体菜谱做法，或输入已有食材让我推荐新手菜。"
    return {
        **state,
        "draft_answer": answer,
        "execution_trace": _trace(state, "进入未知意图兜底节点"),
    }


def quality_check_node(state: AgentState) -> AgentState:
    result = safety_check_service.check(
        intent=state.get("intent", IntentType.UNKNOWN),
        answer=state.get("draft_answer", ""),
        sources=state.get("retrieved_context", []),
        recommendations=state.get("recommendations", []),
        user_ingredients=state.get("user_ingredients", []),
    )
    return {
        **state,
        "quality_check_result": result,
        "execution_trace": _trace(state, f"质量检查：{'通过' if result.passed else '需修复'}"),
    }


def repair_answer_node(state: AgentState) -> AgentState:
    quality = state.get("quality_check_result") or QualityCheckResult(passed=True)
    additions: list[str] = []
    if quality.issues:
        additions.append("系统检查提示：" + "；".join(quality.issues))
    if quality.safety_warnings:
        additions.append("安全提醒：" + "；".join(quality.safety_warnings))

    repaired = state.get("draft_answer", "")
    if additions:
        repaired = f"{repaired}\n\n" + "\n".join(additions)

    return {
        **state,
        "draft_answer": repaired,
        "execution_trace": _trace(state, "根据质量检查结果修复答案"),
    }


def finalize_answer_node(state: AgentState) -> AgentState:
    return {
        **state,
        "final_answer": state.get("draft_answer", ""),
        "execution_trace": _trace(state, "生成最终回复"),
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


def route_after_quality_check(state: AgentState) -> str:
    quality = state.get("quality_check_result")
    if quality and quality.needs_repair:
        return "repair"
    return "finalize"


def _format_recommendation_answer(
    prefix: str,
    recommendations,
) -> str:
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

