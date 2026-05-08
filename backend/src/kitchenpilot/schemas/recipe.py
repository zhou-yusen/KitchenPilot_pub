from pydantic import BaseModel, Field

from kitchenpilot.schemas.enums import ChunkType, Difficulty


class Ingredient(BaseModel):
    """Public schema for an ingredient."""
    id: int
    name: str
    category: str = "other"
    common_score: float = 1.0
    seasons: list[str] = Field(default_factory=list)


class RecipeStep(BaseModel):
    """Public schema for one ordered recipe step."""
    order: int
    content: str
    beginner_tip: str | None = None
    risk_tip: str | None = None


class RecipeIngredient(BaseModel):
    """Public schema for a recipe ingredient requirement."""
    ingredient: str
    amount: str = ""
    required: bool = True


class Recipe(BaseModel):
    """Public schema for a full recipe."""
    id: int
    name: str
    description: str
    difficulty: Difficulty
    time_minutes: int
    beginner_friendly: bool
    cuisine: str = "家常菜"
    seasons: list[str] = Field(default_factory=list)
    ingredients: list[RecipeIngredient]
    steps: list[RecipeStep]
    common_failures: list[str] = Field(default_factory=list)
    substitutions: dict[str, str] = Field(default_factory=dict)
    safety_notes: list[str] = Field(default_factory=list)


class SourceChunk(BaseModel):
    """Public schema for one retrieved RAG source chunk."""
    recipe_id: int
    recipe_name: str
    chunk_type: ChunkType
    content: str
    score: float = 0.0
    metadata: dict[str, object] = Field(default_factory=dict)
