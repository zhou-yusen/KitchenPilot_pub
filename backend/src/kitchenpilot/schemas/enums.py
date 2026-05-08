from enum import StrEnum


class IntentType(StrEnum):
    """Supported high-level user intent values."""
    RECIPE_QA = "recipe_qa"
    INGREDIENT_RECOMMENDATION = "ingredient_recommendation"
    DAILY_RECOMMENDATION = "daily_recommendation"
    UNKNOWN = "unknown"


class Difficulty(StrEnum):
    """Supported recipe difficulty values."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ChunkType(StrEnum):
    """Supported RAG source chunk categories."""
    OVERVIEW = "overview"
    INGREDIENTS = "ingredients"
    STEP = "step"
    FAILURE = "failure"
    SUBSTITUTION = "substitution"
    SAFETY = "safety"

