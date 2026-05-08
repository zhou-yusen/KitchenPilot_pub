from functools import lru_cache

from kitchenpilot.agent import KitchenPilotAgent
from kitchenpilot.recommender.service import RecommendationService
from kitchenpilot.services.recipe_service import RecipeService
from kitchenpilot.services.user_memory_service import UserMemoryService


@lru_cache
def get_agent() -> KitchenPilotAgent:
    return KitchenPilotAgent()


@lru_cache
def get_recipe_service() -> RecipeService:
    return RecipeService()


@lru_cache
def get_recommendation_service() -> RecommendationService:
    return RecommendationService()


@lru_cache
def get_user_memory_service() -> UserMemoryService:
    return UserMemoryService()

