from copy import deepcopy
from typing import Any

from kitchenpilot.services.mock_data import USER_PROFILES


class UserMemoryService:
    def get_user_profile(self, user_id: str) -> dict[str, Any]:
        profile = USER_PROFILES.get(user_id, USER_PROFILES["demo_user"])
        return deepcopy(profile)

    def add_history(self, user_id: str, recipe_id: int, rating: int, feedback: str) -> dict[str, Any]:
        profile = USER_PROFILES.setdefault(
            user_id,
            {
                "liked_ingredients": [],
                "disliked_styles": [],
                "max_time_minutes": 30,
                "recent_recommendations": [],
                "history": [],
            },
        )
        profile["history"].append(
            {"recipe_id": recipe_id, "rating": rating, "feedback": feedback}
        )
        return deepcopy(profile)

