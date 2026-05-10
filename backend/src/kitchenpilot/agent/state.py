from typing import Any, TypedDict

from pydantic import BaseModel, Field

from kitchenpilot.schemas.enums import IntentType, RecommendationType
from kitchenpilot.schemas.quality import QualityCheckResult
from kitchenpilot.schemas.recipe import SourceChunk
from kitchenpilot.schemas.recommendation import RecommendationResult

__all__ = ["AgentState", "AgentStateModel"]


class AgentStateModel(BaseModel):
    """Validated agent state used at API and workflow boundaries."""
    user_id: str = "demo_user"
    session_id: str | None = None
    query: str
    conversation_turns: list[dict[str, Any]] = Field(default_factory=list)
    active_recipe: str | None = None
    rewritten_query: str | None = None
    is_follow_up: bool = False
    intent: IntentType = IntentType.FALLBACK
    intent_confidence: float = 0.0
    intent_source: str = "unknown"
    recommendation_type: RecommendationType | None = None
    needs_clarification: bool = False
    clarification_question: str = ""
    user_ingredients: list[str] = Field(default_factory=list)
    user_profile: dict[str, Any] = Field(default_factory=dict)
    retrieved_context: list[SourceChunk] = Field(default_factory=list)
    recommendations: list[RecommendationResult] = Field(default_factory=list)
    draft_answer: str = ""
    final_answer: str = ""
    quality_check_result: QualityCheckResult | None = None
    execution_trace: list[str] = Field(default_factory=list)


class AgentState(TypedDict, total=False):
    """Mutable dictionary state passed between graph nodes."""
    user_id: str
    session_id: str | None
    query: str
    conversation_turns: list[dict[str, Any]]
    active_recipe: str | None
    rewritten_query: str | None
    is_follow_up: bool
    intent: IntentType
    intent_confidence: float
    intent_source: str
    recommendation_type: RecommendationType | None
    needs_clarification: bool
    clarification_question: str
    user_ingredients: list[str]
    user_profile: dict[str, Any]
    retrieved_context: list[SourceChunk]
    recommendations: list[RecommendationResult]
    draft_answer: str
    final_answer: str
    quality_check_result: QualityCheckResult | None
    execution_trace: list[str]
