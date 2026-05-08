from kitchenpilot.recommender.service import RecommendationService


def test_recommender_prefers_matching_beginner_recipe() -> None:
    """验证食材推荐会优先返回匹配已有食材且适合新手的菜谱。"""
    service = RecommendationService()

    results = service.recommend_by_ingredients("demo_user", ["鸡蛋", "番茄", "土豆"])

    assert results
    assert results[0].recipe_name in {"番茄炒蛋", "酸辣土豆丝"}
    assert results[0].matched_ingredients


def test_daily_recommend_uses_user_preferences() -> None:
    """验证每日推荐会结合用户偏好生成推荐理由。"""
    service = RecommendationService()

    results = service.daily_recommend("demo_user")

    assert results
    assert any("适合新手" in reason for reason in results[0].reasons)
