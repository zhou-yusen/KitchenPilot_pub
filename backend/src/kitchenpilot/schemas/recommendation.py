from pydantic import BaseModel, Field


class RecommendationResult(BaseModel):
    recipe_id: int
    recipe_name: str
    score: float
    matched_ingredients: list[str] = Field(default_factory=list)
    missing_ingredients: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    difficulty: str
    time_minutes: int
    beginner_friendly: bool

