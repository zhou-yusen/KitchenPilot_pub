from fastapi.testclient import TestClient

from kitchenpilot.main import create_app


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_endpoint() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/chat",
        json={"query": "土豆丝怎么炒得脆？", "user_id": "demo_user"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "recipe_qa"
    assert payload["sources"]

