from kitchenpilot.recommender.service import RecommendationService
from kitchenpilot.schemas.enums import RecommendationType


def test_recommender_prefers_matching_beginner_recipe() -> None:
    """验证食材推荐会优先返回匹配已有食材且适合新手的菜谱。"""
    service = RecommendationService()

    results = service.recommend(
        user_id="demo_user",
        recommendation_type=RecommendationType.INGREDIENTS,
        ingredients=["鸡蛋", "番茄", "土豆"],
    )

    assert results
    assert results[0].recipe_name in {"番茄炒蛋", "酸辣土豆丝"}
    assert results[0].matched_ingredients


def test_daily_recommend_uses_user_preferences() -> None:
    """验证每日推荐会结合用户偏好生成推荐理由。"""
    service = RecommendationService()

    results = service.recommend(
        user_id="demo_user",
        recommendation_type=RecommendationType.DAILY,
    )

    assert results
    assert any("适合新手" in reason for reason in results[0].reasons)
    assert any("偏好匹配" in reason for reason in results[0].reasons)
    assert not any("已有食材匹配" in reason for reason in results[0].reasons)


def test_daily_recommend_respects_expert_profile() -> None:
    """验证每日推荐能使用老手画像的更长耗时偏好。"""
    service = RecommendationService()

    results = service.recommend(
        user_id="expert_user",
        recommendation_type=RecommendationType.DAILY,
    )

    assert results
    assert any(item.time_minutes > 30 for item in results)


def test_daily_recommend_differs_by_persona() -> None:
    """验证泛化推荐会根据用户画像给出不同排序。"""
    service = RecommendationService()

    novice = service.recommend(
        user_id="novice_user",
        recommendation_type=RecommendationType.DAILY,
    )
    expert = service.recommend(
        user_id="expert_user",
        recommendation_type=RecommendationType.DAILY,
    )

    assert [item.recipe_name for item in novice] != [item.recipe_name for item in expert]
    assert all(item.difficulty == "easy" for item in novice[:2])
    assert any(item.difficulty in {"medium", "hard"} for item in expert)


def test_recommender_uses_seed_dataset_for_chicken_wings() -> None:
    """验证推荐候选来自 seed 菜谱库，不再退回旧 mock 小列表。"""
    service = RecommendationService()

    results = service.recommend(
        user_id="demo_user",
        recommendation_type=RecommendationType.INGREDIENTS,
        ingredients=["鸡翅"],
    )

    assert results
    assert any("鸡翅" in item.recipe_name for item in results)
