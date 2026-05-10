from kitchenpilot.schemas.enums import Difficulty, RecommendationType
from kitchenpilot.schemas.recipe import Recipe
from kitchenpilot.schemas.recommendation import RecommendationResult
from kitchenpilot.services.recipe_service import RecipeService
from kitchenpilot.services.user_memory_service import UserMemoryService


class RecommendationService:
    """Score recipes and produce recommendation results."""
    def __init__(
        self,
        recipe_service: RecipeService | None = None,
        user_memory_service: UserMemoryService | None = None,
    ) -> None:
        """Initialize this object with its required collaborators."""
        self.recipe_service = recipe_service or RecipeService()
        self.user_memory_service = user_memory_service or UserMemoryService()

    def recommend(
        self,
        *,
        user_id: str,
        recommendation_type: RecommendationType,
        ingredients: list[str] | None = None,
        constraints: dict[str, object] | None = None,
        limit: int = 3,
    ) -> list[RecommendationResult]:
        """Score recipes through the unified recommendation entrypoint."""
        constraints = constraints or {}
        normalized = [item.strip() for item in (ingredients or []) if item.strip()]
        profile = self.user_memory_service.get_user_profile(user_id)
        preference_ingredients: list[str] = []
        if recommendation_type == RecommendationType.DAILY:
            preference_ingredients = list(profile.get("liked_ingredients", []))
            normalized = []
        max_time = constraints.get("max_time")
        if isinstance(max_time, (int, float)):
            profile = {**profile, "max_time_minutes": int(max_time)}
        scored = [
            self._score_recipe(
                recipe,
                normalized,
                profile,
                recommendation_type,
                preference_ingredients,
            )
            for recipe in self.recipe_service.list_recipes()
        ]
        if recommendation_type == RecommendationType.INGREDIENTS and normalized:
            scored = [item for item in scored if item.matched_ingredients]
        scored = [item for item in scored if item.score > 0]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]

    def _score_recipe(
        self,
        recipe: Recipe,
        user_ingredients: list[str],
        profile: dict[str, object],
        recommendation_type: RecommendationType,
        preference_ingredients: list[str] | None = None,
    ) -> RecommendationResult:
        """Calculate one recommendation score and explanation."""
        preference_ingredients = preference_ingredients or []
        required = [item.ingredient for item in recipe.ingredients if item.required]
        matched = [
            item
            for item in required
            if any(self._ingredient_matches(item, user_item) for user_item in user_ingredients)
        ]
        missing = [
            item
            for item in required
            if not any(self._ingredient_matches(item, user_item) for user_item in user_ingredients)
        ]
        preference_matched = [
            item
            for item in required
            if any(
                self._ingredient_matches(item, preferred)
                for preferred in preference_ingredients
            )
        ]

        scoring_matches = (
            preference_matched if recommendation_type == RecommendationType.DAILY else matched
        )
        match_ratio = len(scoring_matches) / len(required) if required else 0.0
        score = match_ratio * 60
        reasons: list[str] = []

        if matched:
            reasons.append(f"已有食材匹配：{'、'.join(matched)}")
        if preference_matched:
            reasons.append(f"偏好食材：{'、'.join(preference_matched)}")
        if missing:
            if recommendation_type == RecommendationType.DAILY:
                reasons.append(f"需要准备：{'、'.join(missing)}")
            else:
                reasons.append(f"还缺少：{'、'.join(missing)}")

        skill_level = str(profile.get("skill_level", "beginner"))
        if recipe.beginner_friendly:
            if skill_level == "expert":
                score += 2
                reasons.append("做法简单，可作为快手菜")
            else:
                score += 15
                reasons.append("适合新手")
        else:
            if skill_level == "expert":
                score += 12
                reasons.append("有一定操作空间，适合老手")
            elif skill_level == "novice":
                score -= 28
                reasons.append("步骤偏复杂，完全新手需要谨慎")
            else:
                score -= 20
                reasons.append("步骤偏复杂，新手需要谨慎")

        if recipe.difficulty == Difficulty.EASY:
            score += 14 if skill_level == "novice" else 10
            if skill_level == "novice":
                reasons.append("难度低，适合从零开始")
        elif recipe.difficulty == Difficulty.MEDIUM:
            if skill_level == "expert":
                score += 8
                reasons.append("中等难度，适合练习火候和调味")
        elif recipe.difficulty == Difficulty.HARD:
            if skill_level == "expert":
                score += 18
                reasons.append("难度较高，适合进阶操作")
            elif skill_level == "novice":
                score -= 28
            else:
                score -= 15

        max_time = int(profile.get("max_time_minutes", 30))
        if recipe.time_minutes <= max_time:
            score += 10
            reasons.append(f"{recipe.time_minutes} 分钟内可完成")
        else:
            score -= 10
            reasons.append(f"耗时约 {recipe.time_minutes} 分钟，超过常用时间偏好")

        recent = set(profile.get("recent_recommendations", []))
        if recipe.id in recent:
            score -= 12
            reasons.append("近期推荐过，降低排序避免重复")

        disliked_styles = profile.get("disliked_styles", [])
        if "复杂肉菜" in disliked_styles and recipe.difficulty == Difficulty.HARD:
            score -= 20

        preferred_difficulties = profile.get("preferred_difficulties", [])
        if recipe.difficulty in preferred_difficulties:
            score += 10
            reasons.append(f"符合 {skill_level} 用户的难度偏好")

        return RecommendationResult(
            recipe_id=recipe.id,
            recipe_name=recipe.name,
            score=round(score, 2),
            matched_ingredients=matched,
            missing_ingredients=missing,
            reasons=reasons,
            difficulty=recipe.difficulty,
            time_minutes=recipe.time_minutes,
            beginner_friendly=recipe.beginner_friendly,
        )

    @staticmethod
    def _ingredient_matches(recipe_ingredient: str, user_ingredient: str) -> bool:
        """Match exact ingredients and common short forms like 鸡翅 -> 鸡翅中."""
        recipe_value = recipe_ingredient.strip()
        user_value = user_ingredient.strip()
        return bool(
            recipe_value
            and user_value
            and (
                recipe_value == user_value
                or recipe_value in user_value
                or user_value in recipe_value
            )
        )
