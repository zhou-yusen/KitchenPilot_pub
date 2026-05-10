from pydantic import BaseModel, Field

from kitchenpilot.schemas.enums import IntentType, RecommendationType
from kitchenpilot.schemas.quality import QualityCheckResult
from kitchenpilot.schemas.recipe import Recipe, SourceChunk
from kitchenpilot.schemas.recommendation import RecommendationResult


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""
    query: str
    user_id: str = "demo_user"
    session_id: str | None = None
    ingredients: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Response body returned by the chat endpoint."""
    session_id: str
    answer: str
    intent: IntentType
    intent_confidence: float = 0.0
    intent_source: str = "unknown"
    recommendation_type: RecommendationType | None = None
    active_recipe: str | None = None
    rewritten_query: str | None = None
    is_follow_up: bool = False
    needs_clarification: bool = False
    clarification_question: str = ""
    recommendations: list[RecommendationResult] = Field(default_factory=list)
    sources: list[SourceChunk] = Field(default_factory=list)
    quality_check: QualityCheckResult | None = None
    execution_trace: list[str] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    """Request body for unified recommendations."""
    user_id: str = "demo_user"
    recommendation_type: RecommendationType
    ingredients: list[str] = Field(default_factory=list)
    constraints: dict[str, object] = Field(default_factory=dict)


class RecommendationResponse(BaseModel):
    """Response body containing recommendation results."""
    recommendations: list[RecommendationResult]


class HistoryCreateRequest(BaseModel):
    """Request body for recording cooking history."""
    user_id: str = "demo_user"
    recipe_id: int
    rating: int = Field(ge=1, le=5)
    feedback: str = ""


class RecipeResponse(BaseModel):
    """Response body containing one recipe."""
    recipe: Recipe

