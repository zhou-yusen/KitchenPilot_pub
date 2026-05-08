from pydantic import BaseModel, Field

from kitchenpilot.schemas.enums import IntentType
from kitchenpilot.schemas.quality import QualityCheckResult
from kitchenpilot.schemas.recipe import Recipe, SourceChunk
from kitchenpilot.schemas.recommendation import RecommendationResult


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""
    query: str
    user_id: str = "demo_user"
    ingredients: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Response body returned by the chat endpoint."""
    answer: str
    intent: IntentType
    intent_confidence: float = 0.0
    intent_source: str = "unknown"
    needs_clarification: bool = False
    clarification_question: str = ""
    recommendations: list[RecommendationResult] = Field(default_factory=list)
    sources: list[SourceChunk] = Field(default_factory=list)
    quality_check: QualityCheckResult | None = None
    execution_trace: list[str] = Field(default_factory=list)


class IngredientRecommendationRequest(BaseModel):
    """Request body for ingredient-based recommendations."""
    user_id: str = "demo_user"
    ingredients: list[str]


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

