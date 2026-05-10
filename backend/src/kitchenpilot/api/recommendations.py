from fastapi import APIRouter, Depends

from kitchenpilot.api.dependencies import get_recommendation_service
from kitchenpilot.recommender.service import RecommendationService
from kitchenpilot.schemas.api import RecommendationRequest, RecommendationResponse

router = APIRouter(prefix="/recommend", tags=["recommendations"])
RECOMMENDATION_SERVICE_DEPENDENCY = Depends(get_recommendation_service)


@router.post("", response_model=RecommendationResponse)
def recommend(
    request: RecommendationRequest,
    service: RecommendationService = RECOMMENDATION_SERVICE_DEPENDENCY,
) -> RecommendationResponse:
    """Generate recommendations through the unified recommendation API."""
    return RecommendationResponse(
        recommendations=service.recommend(
            user_id=request.user_id,
            recommendation_type=request.recommendation_type,
            ingredients=request.ingredients,
            constraints=request.constraints,
        )
    )
