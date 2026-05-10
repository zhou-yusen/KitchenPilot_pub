from fastapi import APIRouter, Depends

from kitchenpilot.agent import KitchenPilotAgent
from kitchenpilot.api.dependencies import get_agent
from kitchenpilot.schemas.agent import AgentStateModel
from kitchenpilot.schemas.api import ChatRequest, ChatResponse
from kitchenpilot.schemas.enums import IntentType
from kitchenpilot.services.conversation_memory_service import conversation_memory_service

router = APIRouter(prefix="/chat", tags=["chat"])
AGENT_DEPENDENCY = Depends(get_agent)


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    agent: KitchenPilotAgent = AGENT_DEPENDENCY,
) -> ChatResponse:
    """Run the chat API request through the KitchenPilot agent."""
    state = AgentStateModel(
        user_id=request.user_id,
        session_id=request.session_id,
        query=request.query,
        user_ingredients=request.ingredients,
    )
    result = agent.invoke(state)
    return ChatResponse(
        session_id=str(result.get("session_id") or ""),
        answer=result.get("final_answer", ""),
        intent=result.get("intent", IntentType.FALLBACK),
        intent_confidence=result.get("intent_confidence", 0.0),
        intent_source=result.get("intent_source", "unknown"),
        recommendation_type=result.get("recommendation_type"),
        active_recipe=result.get("active_recipe"),
        rewritten_query=result.get("rewritten_query"),
        is_follow_up=result.get("is_follow_up", False),
        needs_clarification=result.get("needs_clarification", False),
        clarification_question=result.get("clarification_question", ""),
        recommendations=result.get("recommendations", []),
        sources=result.get("retrieved_context", []),
        quality_check=result.get("quality_check_result"),
        execution_trace=result.get("execution_trace", []),
    )


@router.delete("/sessions/{session_id}")
def delete_chat_session(session_id: str) -> dict[str, object]:
    """Delete one in-memory chat session."""
    deleted = conversation_memory_service.delete(session_id)
    return {"session_id": session_id, "deleted": deleted}

