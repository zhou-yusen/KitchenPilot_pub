from kitchenpilot.agent.nodes.intent_router import _trace
from kitchenpilot.agent.state import AgentState
from kitchenpilot.rag.service import RAGService

rag_service = RAGService()


def recipe_qa_node(state: AgentState) -> AgentState:
    """Answer a recipe question by calling the RAG service."""
    answer_query = state.get("rewritten_query") or state["query"]
    result = rag_service.answer(answer_query, state.get("conversation_turns", []))
    active_recipe = _extract_active_recipe(result.sources) or state.get("active_recipe")
    return {
        **state,
        "active_recipe": active_recipe,
        "retrieved_context": result.sources,
        "draft_answer": result.answer,
        "execution_trace": _trace(
            state,
            f"执行菜谱问答 RAG，命中 {len(result.sources)} 条来源"
            f"{f'，active_recipe={active_recipe}' if active_recipe else ''}",
        ),
    }


def _extract_active_recipe(sources) -> str | None:
    """Extract the active recipe from retrieved source metadata."""
    for source in sources:
        for key in ("recipe_name", "title", "name"):
            value = source.metadata.get(key)
            if value:
                return str(value)
        if source.recipe_name:
            return source.recipe_name
    return None


__all__ = ["recipe_qa_node"]
