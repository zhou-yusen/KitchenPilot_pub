from kitchenpilot.core.config import Settings
from kitchenpilot.rag.service import RAGService


class _FailingQdrantStore:
    """Store that simulates an unavailable Qdrant service."""

    def search(self, query: str, top_k: int):
        """Raise to trigger local fallback retrieval."""
        raise RuntimeError("qdrant unavailable")


def test_rag_retrieve_falls_back_when_qdrant_is_unavailable() -> None:
    """Verify RAG retrieval falls back to local chunks when Qdrant fails."""
    service = RAGService(
        qdrant_store=_FailingQdrantStore(),
        settings=Settings(_env_file=None, rag_use_qdrant=True, llm_provider="mock"),
    )

    results = service.retrieve("土豆丝怎么炒得脆？", top_k=3)

    assert results
    assert all(result.metadata.get("retrieval_source") == "local" for result in results)
    assert all(result.score > 0 for result in results)


def test_rag_retrieve_returns_qdrant_chunks_when_available() -> None:
    """Verify Qdrant results are returned before local fallback."""
    local_service = RAGService(settings=Settings(_env_file=None, rag_use_qdrant=False))
    qdrant_chunk = local_service.retrieve("土豆丝怎么炒得脆？", top_k=1)[0].model_copy(
        update={"score": 0.99, "metadata": {"retrieval_source": "qdrant"}}
    )

    class _WorkingQdrantStore:
        """Store that returns one prepared Qdrant chunk."""

        def search(self, query: str, top_k: int):
            """Return the prepared Qdrant chunk."""
            return [qdrant_chunk]

    service = RAGService(
        qdrant_store=_WorkingQdrantStore(),
        settings=Settings(_env_file=None, rag_use_qdrant=True, llm_provider="mock"),
    )

    results = service.retrieve("土豆丝怎么炒得脆？", top_k=3)

    assert results == [qdrant_chunk]
    assert results[0].metadata["retrieval_source"] == "qdrant"
