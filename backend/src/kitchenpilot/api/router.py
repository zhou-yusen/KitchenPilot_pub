from fastapi import APIRouter

from kitchenpilot.api.chat import router as chat_router
from kitchenpilot.api.history import router as history_router
from kitchenpilot.api.recipes import router as recipes_router
from kitchenpilot.api.recommendations import router as recommendations_router

api_router = APIRouter()
api_router.include_router(chat_router)
api_router.include_router(recommendations_router)
api_router.include_router(recipes_router)
api_router.include_router(history_router)

