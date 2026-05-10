from fastapi.testclient import TestClient

from kitchenpilot.main import create_app
from kitchenpilot.services.conversation_memory_service import conversation_memory_service


def test_health_endpoint() -> None:
    """验证健康检查接口可以正常返回服务状态。"""
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_endpoint() -> None:
    """验证聊天接口能触发 Agent 流程并返回菜谱问答结果。"""
    conversation_memory_service.clear()
    client = TestClient(create_app())

    response = client.post(
        "/api/chat",
        json={"query": "土豆丝怎么炒得脆？", "user_id": "demo_user"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"]
    assert payload["intent"] == "recipe_qa"
    assert payload["sources"]


def test_chat_recommendation_endpoint() -> None:
    """验证聊天接口能自动路由到统一推荐 intent。"""
    conversation_memory_service.clear()
    client = TestClient(create_app())

    response = client.post(
        "/api/chat",
        json={"query": "我有鸡蛋和土豆，推荐一道菜", "user_id": "demo_user"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "recommendation"
    assert payload["recommendation_type"] == "ingredients"
    assert payload["recommendations"]


def test_chat_recommendation_uses_seed_recipes_for_chicken_wings() -> None:
    """验证食材推荐使用 seed 菜谱库和食材别名匹配。"""
    conversation_memory_service.clear()
    client = TestClient(create_app())

    response = client.post(
        "/api/chat",
        json={"query": "我有鸡翅，推荐一道菜", "user_id": "demo_user"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "recommendation"
    assert payload["recommendation_type"] == "ingredients"
    assert any("鸡翅" in item["recipe_name"] for item in payload["recommendations"])


def test_chat_daily_recommendation_endpoint() -> None:
    """验证聊天接口能自动路由到每日推荐子类型。"""
    conversation_memory_service.clear()
    client = TestClient(create_app())

    response = client.post(
        "/api/chat",
        json={"query": "今天吃什么？", "user_id": "demo_user"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "recommendation"
    assert payload["recommendation_type"] == "daily"
    assert payload["recommendations"]


def test_chat_follow_up_uses_session_memory() -> None:
    """验证同一 session 的追问能继承上一轮 active_recipe。"""
    conversation_memory_service.clear()
    client = TestClient(create_app())
    session_id = "api_follow_up_session"

    first = client.post(
        "/api/chat",
        json={
            "query": "可乐鸡翅怎么做？只告诉我步骤就好，不要太多的符号",
            "user_id": "demo_user",
            "session_id": session_id,
        },
    )
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["active_recipe"] == "可乐鸡翅"

    second = client.post(
        "/api/chat",
        json={
            "query": "生抽要下多少？还需要别的调料吗？",
            "user_id": "demo_user",
            "session_id": session_id,
        },
    )

    assert second.status_code == 200
    payload = second.json()
    assert payload["intent"] == "recipe_qa"
    assert payload["intent_source"] == "session_memory"
    assert payload["is_follow_up"] is True
    assert payload["active_recipe"] == "可乐鸡翅"
    assert "可乐鸡翅" in payload["rewritten_query"]


def test_chat_sessions_do_not_share_active_recipe() -> None:
    """验证不同 session 不共享 active_recipe。"""
    conversation_memory_service.clear()
    client = TestClient(create_app())

    first = client.post(
        "/api/chat",
        json={
            "query": "可乐鸡翅怎么做？",
            "user_id": "demo_user",
            "session_id": "session_a",
        },
    )
    assert first.status_code == 200
    assert first.json()["active_recipe"] == "可乐鸡翅"

    second = client.post(
        "/api/chat",
        json={
            "query": "生抽要下多少？还需要别的调料吗？",
            "user_id": "demo_user",
            "session_id": "session_b",
        },
    )

    assert second.status_code == 200
    payload = second.json()
    assert payload["is_follow_up"] is False
    assert payload["rewritten_query"] is None
    assert payload["active_recipe"] != "可乐鸡翅"


def test_chat_learning_seed_recipe_routes_to_recipe_qa() -> None:
    """验证 seed 菜谱名能被 Router 识别为菜谱问答。"""
    conversation_memory_service.clear()
    client = TestClient(create_app())

    response = client.post(
        "/api/chat",
        json={"query": "我想学咸蛋黄鸡翅", "user_id": "demo_user"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "recipe_qa"
    assert payload["active_recipe"] == "咸蛋黄鸡翅"


def test_chat_short_condiment_question_asks_for_recipe_context() -> None:
    """验证无上下文调料短问不会被误判为食材推荐。"""
    conversation_memory_service.clear()
    client = TestClient(create_app())

    response = client.post(
        "/api/chat",
        json={"query": "用不用下盐？", "user_id": "demo_user"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "fallback"
    assert payload["needs_clarification"] is True
    assert "哪道菜" in payload["answer"]


def test_delete_chat_session_clears_backend_memory() -> None:
    """验证删除 session 会释放后端内存记忆。"""
    conversation_memory_service.clear()
    client = TestClient(create_app())
    session_id = "delete_memory_session"

    first = client.post(
        "/api/chat",
        json={
            "query": "可乐鸡翅怎么做？",
            "user_id": "demo_user",
            "session_id": session_id,
        },
    )
    assert first.status_code == 200
    assert conversation_memory_service.load(session_id)

    deleted = client.delete(f"/api/chat/sessions/{session_id}")

    assert deleted.status_code == 200
    assert deleted.json() == {"session_id": session_id, "deleted": True}
    assert conversation_memory_service.load(session_id) == []

    deleted_again = client.delete(f"/api/chat/sessions/{session_id}")
    assert deleted_again.status_code == 200
    assert deleted_again.json()["deleted"] is False


def test_unified_recommend_endpoint() -> None:
    """验证统一推荐接口支持食材推荐。"""
    client = TestClient(create_app())

    response = client.post(
        "/api/recommend",
        json={
            "user_id": "demo_user",
            "recommendation_type": "ingredients",
            "ingredients": ["鸡蛋", "土豆"],
        },
    )

    assert response.status_code == 200
    assert response.json()["recommendations"]


def test_unified_recommend_endpoint_daily_mode() -> None:
    """验证统一推荐接口支持每日推荐。"""
    client = TestClient(create_app())

    response = client.post(
        "/api/recommend",
        json={"user_id": "demo_user", "recommendation_type": "daily"},
    )

    assert response.status_code == 200
    assert response.json()["recommendations"]
