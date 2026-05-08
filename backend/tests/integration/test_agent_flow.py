from kitchenpilot.agent import KitchenPilotAgent
from kitchenpilot.schemas.agent import AgentStateModel
from kitchenpilot.schemas.enums import IntentType


def test_agent_runs_recipe_qa_flow() -> None:
    """Verify the agent can run a recipe QA flow and return evidence."""
    agent = KitchenPilotAgent()

    result = agent.invoke(AgentStateModel(query="土豆丝怎么炒得脆？"))

    assert result["intent"] == IntentType.RECIPE_QA
    assert "土豆" in result["final_answer"]
    assert result["retrieved_context"]
    assert result["execution_trace"]


def test_agent_runs_ingredient_recommendation_flow() -> None:
    """Verify the agent can recommend recipes from available ingredients."""
    agent = KitchenPilotAgent()

    result = agent.invoke(
        AgentStateModel(query="我有鸡蛋、番茄和土豆，推荐一道简单菜。")
    )

    assert result["intent"] == IntentType.INGREDIENT_RECOMMENDATION
    assert result["recommendations"]
    assert "推荐" in result["final_answer"]


def test_agent_unknown_intent_returns_clarification_question() -> None:
    """Verify unclear requests ask the user to choose a supported cooking task."""
    agent = KitchenPilotAgent()

    result = agent.invoke(AgentStateModel(query="随便帮我想想"))

    assert result["intent"] == IntentType.UNKNOWN
    assert result["needs_clarification"]
    assert "根据已有食材推荐菜" in result["final_answer"]
    assert "按你的偏好推荐今天吃什么" in result["final_answer"]
    assert "回答某道菜的具体做法" in result["final_answer"]
