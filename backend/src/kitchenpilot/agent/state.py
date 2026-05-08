from typing import Any, TypedDict

from pydantic import BaseModel, Field

from kitchenpilot.schemas.enums import IntentType
from kitchenpilot.schemas.quality import QualityCheckResult
from kitchenpilot.schemas.recipe import SourceChunk
from kitchenpilot.schemas.recommendation import RecommendationResult

__all__ = ["AgentState", "AgentStateModel"]


class AgentStateModel(BaseModel):
    """Validated agent state used at API and workflow boundaries."""
    user_id: str = "demo_user"
    query: str
    intent: IntentType = IntentType.UNKNOWN
    intent_confidence: float = 0.0
    intent_source: str = "unknown"
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
    query: str
    intent: IntentType
    intent_confidence: float
    intent_source: str
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
