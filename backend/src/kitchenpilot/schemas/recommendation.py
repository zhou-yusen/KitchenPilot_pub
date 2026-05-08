from pydantic import BaseModel, Field


class RecommendationResult(BaseModel):
    """Public schema for one recipe recommendation."""
    recipe_id: int
    recipe_name: str
    score: float
    matched_ingredients: list[str] = Field(default_factory=list)
    missing_ingredients: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    difficulty: str
    time_minutes: int
    beginner_friendly: bool

