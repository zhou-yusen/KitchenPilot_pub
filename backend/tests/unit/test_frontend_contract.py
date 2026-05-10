from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_frontend_session_ui_contract() -> None:
    """Verify the debug UI exposes session controls and KitchenPilot naming."""
    index = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert "KitchenPilot 调试聊天窗口" in index
    assert "id=\"sessionList\"" in index
    assert "id=\"newSession\"" in index
    assert "novice_user" in index
    assert "beginner_user" in index
    assert "expert_user" in index
    assert "KitchenPilot" in app
    assert "session_id" in app
    assert "localStorage" in app
