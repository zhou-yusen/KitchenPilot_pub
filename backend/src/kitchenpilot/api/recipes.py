from fastapi import APIRouter, Depends, HTTPException

from kitchenpilot.api.dependencies import get_recipe_service
from kitchenpilot.schemas.api import RecipeResponse
from kitchenpilot.services.recipe_service import RecipeService

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(
    recipe_id: int,
    service: RecipeService = Depends(get_recipe_service),
) -> RecipeResponse:
    recipe = service.get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return RecipeResponse(recipe=recipe)

