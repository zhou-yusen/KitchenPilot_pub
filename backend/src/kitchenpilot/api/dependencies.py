from functools import lru_cache

from kitchenpilot.agent import KitchenPilotAgent
from kitchenpilot.recommender.service import RecommendationService
from kitchenpilot.services.recipe_service import RecipeService
from kitchenpilot.services.user_memory_service import UserMemoryService


@lru_cache
def get_agent() -> KitchenPilotAgent:
    """Return the cached KitchenPilot agent instance."""
    return KitchenPilotAgent()


@lru_cache
def get_recipe_service() -> RecipeService:
    """Return the cached recipe service instance."""
    return RecipeService()


@lru_cache
def get_recommendation_service() -> RecommendationService:
    """Return the cached recommendation service instance."""
    return RecommendationService()


@lru_cache
def get_user_memory_service() -> UserMemoryService:
    """Return the cached user memory service instance."""
    return UserMemoryService()

