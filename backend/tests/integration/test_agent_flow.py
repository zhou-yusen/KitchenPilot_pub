from kitchenpilot.agent import KitchenPilotAgent
from kitchenpilot.schemas.agent import AgentStateModel
from kitchenpilot.schemas.enums import IntentType


def test_agent_runs_recipe_qa_flow() -> None:
    agent = KitchenPilotAgent()

    result = agent.invoke(AgentStateModel(query="土豆丝怎么炒得脆？"))

    assert result["intent"] == IntentType.RECIPE_QA
    assert "土豆" in result["final_answer"]
    assert result["retrieved_context"]
    assert result["execution_trace"]


def test_agent_runs_ingredient_recommendation_flow() -> None:
    agent = KitchenPilotAgent()

    result = agent.invoke(
        AgentStateModel(query="我有鸡蛋、番茄、土豆，推荐一道简单菜。")
    )

    assert result["intent"] == IntentType.INGREDIENT_RECOMMENDATION
    assert result["recommendations"]
    assert "推荐" in result["final_answer"]

