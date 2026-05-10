from copy import deepcopy
from typing import Any

from kitchenpilot.services.user_profiles import get_persona_profile, resolve_user_id


class UserMemoryService:
    """Store and retrieve lightweight user preference data."""

    def __init__(self) -> None:
        """Initialize runtime history on top of predefined personas."""
        self._runtime_profiles: dict[str, dict[str, Any]] = {}

    def get_user_profile(self, user_id: str) -> dict[str, Any]:
        """Return a user profile or a default empty profile."""
        resolved = resolve_user_id(user_id)
        profile = self._runtime_profiles.get(resolved) or get_persona_profile(resolved)
        return deepcopy(profile)

    def add_history(
        self,
        user_id: str,
        recipe_id: int,
        rating: int,
        feedback: str,
    ) -> dict[str, Any]:
        """Append one cooking-history entry to a user profile."""
        resolved = resolve_user_id(user_id)
        profile = self._runtime_profiles.setdefault(resolved, get_persona_profile(resolved))
        profile["history"].append(
            {"recipe_id": recipe_id, "rating": rating, "feedback": feedback}
        )
        recent = profile.setdefault("recent_recommendations", [])
        if recipe_id not in recent:
            recent.append(recipe_id)
        return deepcopy(profile)

