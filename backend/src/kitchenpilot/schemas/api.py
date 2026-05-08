from pydantic import BaseModel, Field

from kitchenpilot.schemas.enums import IntentType
from kitchenpilot.schemas.quality import QualityCheckResult
from kitchenpilot.schemas.recipe import Recipe, SourceChunk
from kitchenpilot.schemas.recommendation import RecommendationResult


class ChatRequest(BaseModel):
    query: str
    user_id: str = "demo_user"
    ingredients: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    intent: IntentType
    recommendations: list[RecommendationResult] = Field(default_factory=list)
    sources: list[SourceChunk] = Field(default_factory=list)
    quality_check: QualityCheckResult | None = None
    execution_trace: list[str] = Field(default_factory=list)


class IngredientRecommendationRequest(BaseModel):
    user_id: str = "demo_user"
    ingredients: list[str]


class RecommendationResponse(BaseModel):
    recommendations: list[RecommendationResult]


class HistoryCreateRequest(BaseModel):
    user_id: str = "demo_user"
    recipe_id: int
    rating: int = Field(ge=1, le=5)
    feedback: str = ""


class RecipeResponse(BaseModel):
    recipe: Recipe

