from kitchenpilot.schemas.enums import Difficulty
from kitchenpilot.schemas.recipe import Recipe
from kitchenpilot.schemas.recommendation import RecommendationResult
from kitchenpilot.services.recipe_service import RecipeService
from kitchenpilot.services.user_memory_service import UserMemoryService


class RecommendationService:
    def __init__(
        self,
        recipe_service: RecipeService | None = None,
        user_memory_service: UserMemoryService | None = None,
    ) -> None:
        self.recipe_service = recipe_service or RecipeService()
        self.user_memory_service = user_memory_service or UserMemoryService()

    def recommend_by_ingredients(
        self, user_id: str, ingredients: list[str], limit: int = 3
    ) -> list[RecommendationResult]:
        normalized = [item.strip() for item in ingredients if item.strip()]
        profile = self.user_memory_service.get_user_profile(user_id)
        scored = [
            self._score_recipe(recipe, normalized, profile)
            for recipe in self.recipe_service.list_recipes()
        ]
        scored = [item for item in scored if item.score > 0]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]

    def daily_recommend(self, user_id: str, limit: int = 3) -> list[RecommendationResult]:
        profile = self.user_memory_service.get_user_profile(user_id)
        liked = list(profile.get("liked_ingredients", []))
        return self.recommend_by_ingredients(user_id=user_id, ingredients=liked, limit=limit)

    def _score_recipe(
        self, recipe: Recipe, user_ingredients: list[str], profile: dict[str, object]
    ) -> RecommendationResult:
        required = [item.ingredient for item in recipe.ingredients if item.required]
        matched = [item for item in required if item in user_ingredients]
        missing = [item for item in required if item not in user_ingredients]

        match_ratio = len(matched) / len(required) if required else 0.0
        score = match_ratio * 60
        reasons: list[str] = []

        if matched:
            reasons.append(f"已有食材匹配：{'、'.join(matched)}")
        if missing:
            reasons.append(f"还缺少：{'、'.join(missing)}")

        if recipe.beginner_friendly:
            score += 15
            reasons.append("适合新手")
        else:
            score -= 20
            reasons.append("步骤偏复杂，新手需要谨慎")

        if recipe.difficulty == Difficulty.EASY:
            score += 10
        elif recipe.difficulty == Difficulty.HARD:
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
