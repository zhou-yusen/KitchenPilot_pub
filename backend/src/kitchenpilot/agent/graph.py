from kitchenpilot.agent.nodes import (
    daily_recommendation_node,
    finalize_answer_node,
    ingredient_recommendation_node,
    load_user_history_node,
    parse_input_node,
    quality_check_node,
    recipe_qa_node,
    repair_answer_node,
    route_after_intent,
    route_after_quality_check,
    route_intent_node,
    unknown_intent_node,
)
from kitchenpilot.agent.state import AgentState, AgentStateModel


class KitchenPilotAgent:
    def __init__(self) -> None:
        self._graph = self._build_graph()

    def invoke(self, state: AgentState | AgentStateModel) -> AgentState:
        initial = state.model_dump() if isinstance(state, AgentStateModel) else dict(state)
        if self._graph is None:
            return self._invoke_without_langgraph(initial)
        return self._graph.invoke(initial)

    def _build_graph(self):
        try:
            from langgraph.graph import END, StateGraph
        except ImportError:
            return None

        workflow = StateGraph(AgentState)
        workflow.add_node("parse_input", parse_input_node)
        workflow.add_node("load_user_history", load_user_history_node)
        workflow.add_node("route_intent", route_intent_node)
        workflow.add_node("recipe_qa", recipe_qa_node)
        workflow.add_node("ingredient_recommendation", ingredient_recommendation_node)
        workflow.add_node("daily_recommendation", daily_recommendation_node)
        workflow.add_node("unknown", unknown_intent_node)
        workflow.add_node("quality_check", quality_check_node)
        workflow.add_node("repair", repair_answer_node)
        workflow.add_node("finalize", finalize_answer_node)

        workflow.set_entry_point("parse_input")
        workflow.add_edge("parse_input", "load_user_history")
        workflow.add_edge("load_user_history", "route_intent")
        workflow.add_conditional_edges(
            "route_intent",
            route_after_intent,
            {
                "recipe_qa": "recipe_qa",
                "ingredient_recommendation": "ingredient_recommendation",
                "daily_recommendation": "daily_recommendation",
                "unknown": "unknown",
            },
        )
        workflow.add_edge("recipe_qa", "quality_check")
        workflow.add_edge("ingredient_recommendation", "quality_check")
        workflow.add_edge("daily_recommendation", "quality_check")
        workflow.add_edge("unknown", "quality_check")
        workflow.add_conditional_edges(
            "quality_check",
            route_after_quality_check,
            {"repair": "repair", "finalize": "finalize"},
        )
        workflow.add_edge("repair", "finalize")
        workflow.add_edge("finalize", END)
        return workflow.compile()

    def _invoke_without_langgraph(self, state: AgentState) -> AgentState:
        state = parse_input_node(state)
        state = load_user_history_node(state)
        state = route_intent_node(state)

        route = route_after_intent(state)
        if route == "recipe_qa":
            state = recipe_qa_node(state)
        elif route == "ingredient_recommendation":
            state = ingredient_recommendation_node(state)
        elif route == "daily_recommendation":
            state = daily_recommendation_node(state)
        else:
            state = unknown_intent_node(state)

        state = quality_check_node(state)
        if route_after_quality_check(state) == "repair":
            state = repair_answer_node(state)
        return finalize_answer_node(state)
