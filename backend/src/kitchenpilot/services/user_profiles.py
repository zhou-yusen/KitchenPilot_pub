from copy import deepcopy
from typing import Any

USER_PERSONAS: dict[str, dict[str, Any]] = {
    "novice_user": {
        "display_name": "完全新手",
        "skill_level": "novice",
        "liked_ingredients": ["鸡蛋", "番茄", "土豆"],
        "disliked_styles": ["复杂肉菜", "油炸", "大火爆炒"],
        "preferred_difficulties": ["easy"],
        "max_time_minutes": 20,
        "recent_recommendations": [],
        "history": [],
    },
    "beginner_user": {
        "display_name": "入门用户",
        "skill_level": "beginner",
        "liked_ingredients": ["鸡蛋", "土豆", "鸡翅", "生菜"],
        "disliked_styles": ["复杂肉菜"],
        "preferred_difficulties": ["easy", "medium"],
        "max_time_minutes": 30,
        "recent_recommendations": [1],
        "history": [
            {"recipe_id": 1, "rating": 5, "feedback": "简单好吃"},
            {"recipe_id": 4, "rating": 2, "feedback": "太难，收汁容易糊"},
        ],
    },
    "expert_user": {
        "display_name": "技艺高超的老手",
        "skill_level": "expert",
        "liked_ingredients": ["牛腩", "鲜鱼", "鸡翅", "虾", "五花肉"],
        "disliked_styles": [],
        "preferred_difficulties": ["medium", "hard"],
        "max_time_minutes": 120,
        "recent_recommendations": [],
        "history": [
            {"recipe_id": 4, "rating": 5, "feedback": "能稳定控制火候和收汁"},
            {"recipe_id": 13, "rating": 5, "feedback": "喜欢慢炖和复杂调味"},
        ],
    },
}

DEFAULT_USER_ID = "beginner_user"
USER_ALIASES = {
    "demo_user": DEFAULT_USER_ID,
    "default_user": DEFAULT_USER_ID,
}


def resolve_user_id(user_id: str) -> str:
    """Resolve aliases to a known persona id."""
    clean_id = (user_id or "").strip()
    return USER_ALIASES.get(clean_id, clean_id or DEFAULT_USER_ID)


def get_persona_profile(user_id: str) -> dict[str, Any]:
    """Return a copy of a predefined persona profile."""
    resolved = resolve_user_id(user_id)
    profile = USER_PERSONAS.get(resolved, USER_PERSONAS[DEFAULT_USER_ID])
    return deepcopy(profile)
