from fastapi import APIRouter, Depends

from kitchenpilot.api.dependencies import get_recommendation_service
from kitchenpilot.recommender.service import RecommendationService
from kitchenpilot.schemas.api import IngredientRecommendationRequest, RecommendationResponse

router = APIRouter(prefix="/recommend", tags=["recommendations"])


@router.post("/ingredients", response_model=RecommendationResponse)
def recommend_by_ingredients(
    request: IngredientRecommendationRequest,
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationResponse:
    """Score recipes against user-provided ingredients."""
    return RecommendationResponse(
        recommendations=service.recommend_by_ingredients(
            user_id=request.user_id,
            ingredients=request.ingredients,
        )
    )


@router.get("/daily/{user_id}", response_model=RecommendationResponse)
def daily_recommend(
    user_id: str,
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationResponse:
    """Build daily recommendations from stored user preferences."""
    return RecommendationResponse(recommendations=service.daily_recommend(user_id=user_id))

