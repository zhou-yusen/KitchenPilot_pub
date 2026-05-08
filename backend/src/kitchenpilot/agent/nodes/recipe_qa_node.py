from kitchenpilot.agent.nodes.intent_router import _trace
from kitchenpilot.agent.state import AgentState
from kitchenpilot.rag.service import RAGService


rag_service = RAGService()


def recipe_qa_node(state: AgentState) -> AgentState:
    result = rag_service.answer(state["query"])
    return {
        **state,
        "retrieved_context": result.sources,
        "draft_answer": result.answer,
        "execution_trace": _trace(state, f"执行菜谱问答 RAG，命中 {len(result.sources)} 条来源"),
    }


__all__ = ["recipe_qa_node"]
