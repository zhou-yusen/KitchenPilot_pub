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
    PREP = "prep"
    STEP = "step"
    BEGINNER_TIP = "beginner_tip"
    FAILURE_REASON = "failure_reason"
    SUBSTITUTION = "substitution"
    SAFETY_NOTE = "safety_note"

