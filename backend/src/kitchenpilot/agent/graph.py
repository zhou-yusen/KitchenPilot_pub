from kitchenpilot.agent.nodes import (
    fallback_node,
    finalize_answer_node,
    load_session_memory_node,
    load_user_history_node,
    parse_input_node,
    quality_check_node,
    recipe_qa_node,
    recommendation_node,
    repair_answer_node,
    route_after_intent,
    route_after_quality_check,
    route_intent_node,
    save_session_memory_node,
)
from kitchenpilot.agent.state import AgentState, AgentStateModel


class KitchenPilotAgent:
    """Build and execute the KitchenPilot LangGraph workflow."""
    def __init__(self) -> None:
        """Initialize this object with its required collaborators."""
        self._graph = self._build_graph()

    def invoke(self, state: AgentState | AgentStateModel) -> AgentState:
        """Run the agent workflow for one input state and return the final state."""
        initial = state.model_dump() if isinstance(state, AgentStateModel) else dict(state)
        if self._graph is None:
            return self._invoke_without_langgraph(initial)
        return self._graph.invoke(initial)

    def _build_graph(self):
        """Create the LangGraph node and edge wiring for the agent workflow."""
        try:
            from langgraph.graph import END, StateGraph
        except ImportError:
            return None

        workflow = StateGraph(AgentState)
        workflow.add_node("parse_input", parse_input_node)
        workflow.add_node("load_session_memory", load_session_memory_node)
        workflow.add_node("load_user_history", load_user_history_node)
        workflow.add_node("route_intent", route_intent_node)
        workflow.add_node("recipe_qa", recipe_qa_node)
        workflow.add_node("recommendation", recommendation_node)
        workflow.add_node("fallback", fallback_node)
        workflow.add_node("quality_check", quality_check_node)
        workflow.add_node("repair", repair_answer_node)
        workflow.add_node("finalize", finalize_answer_node)
        workflow.add_node("save_session_memory", save_session_memory_node)

        workflow.set_entry_point("parse_input")
        workflow.add_edge("parse_input", "load_session_memory")
        workflow.add_edge("load_session_memory", "load_user_history")
        workflow.add_edge("load_user_history", "route_intent")
        workflow.add_conditional_edges(
            "route_intent",
            route_after_intent,
            {
                "recipe_qa": "recipe_qa",
                "recommendation": "recommendation",
                "fallback": "fallback",
            },
        )
        workflow.add_edge("recipe_qa", "quality_check")
        workflow.add_edge("recommendation", "quality_check")
        workflow.add_edge("fallback", "quality_check")
        workflow.add_conditional_edges(
            "quality_check",
            route_after_quality_check,
            {"repair": "repair", "finalize": "finalize"},
        )
        workflow.add_edge("repair", "finalize")
        workflow.add_edge("finalize", "save_session_memory")
        workflow.add_edge("save_session_memory", END)
        return workflow.compile()

    def _invoke_without_langgraph(self, state: AgentState) -> AgentState:
        """Run the agent workflow sequentially when LangGraph is unavailable."""
        state = parse_input_node(state)
        state = load_session_memory_node(state)
        state = load_user_history_node(state)
        state = route_intent_node(state)

        route = route_after_intent(state)
        if route == "recipe_qa":
            state = recipe_qa_node(state)
        elif route == "recommendation":
            state = recommendation_node(state)
        else:
            state = fallback_node(state)

        state = quality_check_node(state)
        if route_after_quality_check(state) == "repair":
            state = repair_answer_node(state)
        state = finalize_answer_node(state)
        return save_session_memory_node(state)
