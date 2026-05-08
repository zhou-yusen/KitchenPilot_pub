from enum import StrEnum


class IntentType(StrEnum):
    RECIPE_QA = "recipe_qa"
    INGREDIENT_RECOMMENDATION = "ingredient_recommendation"
    DAILY_RECOMMENDATION = "daily_recommendation"
    UNKNOWN = "unknown"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ChunkType(StrEnum):
    PREP = "prep"
    STEP = "step"
    BEGINNER_TIP = "beginner_tip"
    FAILURE_REASON = "failure_reason"
    SUBSTITUTION = "substitution"
    SAFETY_NOTE = "safety_note"

