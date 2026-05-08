from kitchenpilot.agent.nodes.intent_router import _trace
from kitchenpilot.agent.state import AgentState
from kitchenpilot.schemas.enums import IntentType
from kitchenpilot.schemas.quality import QualityCheckResult
from kitchenpilot.services.safety_check_service import SafetyCheckService


safety_check_service = SafetyCheckService()


def quality_check_node(state: AgentState) -> AgentState:
    """Run safety and quality checks against the draft answer."""
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
        "execution_trace": _trace(
            state,
            f"质量检查：{'通过' if result.passed else '需要修复'}",
        ),
    }


def repair_answer_node(state: AgentState) -> AgentState:
    """Append quality issues and safety warnings to the draft answer."""
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
    """Copy the current draft answer into the final answer field."""
    return {
        **state,
        "final_answer": state.get("draft_answer", ""),
        "execution_trace": _trace(state, "生成最终回答"),
    }


def route_after_quality_check(state: AgentState) -> str:
    """Choose whether to repair or finalize the answer."""
    quality = state.get("quality_check_result")
    if quality and quality.needs_repair:
        return "repair"
    return "finalize"


__all__ = [
    "finalize_answer_node",
    "quality_check_node",
    "repair_answer_node",
    "route_after_quality_check",
]
