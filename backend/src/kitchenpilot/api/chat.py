from fastapi import APIRouter, Depends

from kitchenpilot.agent import KitchenPilotAgent
from kitchenpilot.api.dependencies import get_agent
from kitchenpilot.schemas.agent import AgentStateModel
from kitchenpilot.schemas.api import ChatRequest, ChatResponse
from kitchenpilot.schemas.enums import IntentType

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    agent: KitchenPilotAgent = Depends(get_agent),
) -> ChatResponse:
    state = AgentStateModel(
        user_id=request.user_id,
        query=request.query,
        user_ingredients=request.ingredients,
    )
    result = agent.invoke(state)
    return ChatResponse(
        answer=result.get("final_answer", ""),
        intent=result.get("intent", IntentType.UNKNOWN),
        recommendations=result.get("recommendations", []),
        sources=result.get("retrieved_context", []),
        quality_check=result.get("quality_check_result"),
        execution_trace=result.get("execution_trace", []),
    )

