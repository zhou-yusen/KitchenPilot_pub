from kitchenpilot.services.user_memory_service import UserMemoryService
from kitchenpilot.services.user_profiles import USER_PERSONAS


def test_user_personas_include_three_classic_profiles() -> None:
    """验证测试前端使用的三个典型用户画像存在。"""
    assert USER_PERSONAS["novice_user"]["display_name"] == "完全新手"
    assert USER_PERSONAS["beginner_user"]["display_name"] == "入门用户"
    assert USER_PERSONAS["expert_user"]["display_name"] == "技艺高超的老手"


def test_demo_user_aliases_beginner_profile() -> None:
    """验证旧 demo_user 兼容入门用户画像。"""
    service = UserMemoryService()

    profile = service.get_user_profile("demo_user")

    assert profile["skill_level"] == "beginner"
    assert "鸡翅" in profile["liked_ingredients"]


def test_add_history_updates_runtime_copy_only() -> None:
    """验证历史写入只更新运行时副本，不污染预设画像。"""
    service = UserMemoryService()

    updated = service.add_history("novice_user", recipe_id=7, rating=4, feedback="能做")
    fresh_service_profile = UserMemoryService().get_user_profile("novice_user")

    assert updated["history"][-1]["recipe_id"] == 7
    assert 7 in updated["recent_recommendations"]
    assert fresh_service_profile["history"] == []
