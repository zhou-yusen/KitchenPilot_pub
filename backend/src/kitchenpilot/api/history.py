from fastapi import APIRouter, Depends

from kitchenpilot.api.dependencies import get_user_memory_service
from kitchenpilot.schemas.api import HistoryCreateRequest
from kitchenpilot.services.user_memory_service import UserMemoryService

router = APIRouter(prefix="/history", tags=["history"])


@router.post("")
def create_history(
    request: HistoryCreateRequest,
    service: UserMemoryService = Depends(get_user_memory_service),
) -> dict[str, object]:
    """Record a user cooking-history entry."""
    profile = service.add_history(
        user_id=request.user_id,
        recipe_id=request.recipe_id,
        rating=request.rating,
        feedback=request.feedback,
    )
    return {"user_id": request.user_id, "profile": profile}

