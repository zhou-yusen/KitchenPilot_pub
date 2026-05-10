from enum import StrEnum


class IntentType(StrEnum):
    """Supported high-level user intent values."""
    RECIPE_QA = "recipe_qa"
    RECOMMENDATION = "recommendation"
    FALLBACK = "fallback"


class RecommendationType(StrEnum):
    """Supported recommendation subtypes."""
    INGREDIENTS = "ingredients"
    DAILY = "daily"


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

