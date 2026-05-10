from kitchenpilot.core.config import Settings
from kitchenpilot.rag.service import RAGService
from kitchenpilot.schemas.enums import ChunkType
from kitchenpilot.schemas.recipe import SourceChunk


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


def test_rag_retrieve_reranks_qdrant_chunks_by_question_intent() -> None:
    """Verify intent cues prefer matching chunk types over raw Qdrant order."""
    chunks = [
        _chunk(ChunkType.STEP, score=0.95),
        _chunk(ChunkType.SAFETY, score=0.70),
        _chunk(ChunkType.FAILURE, score=0.90),
    ]

    class _WorkingQdrantStore:
        """Store that returns intentionally unsorted semantic chunks."""

        def search(self, query: str, top_k: int):
            """Return the prepared chunks."""
            return chunks

    service = RAGService(
        qdrant_store=_WorkingQdrantStore(),
        settings=Settings(_env_file=None, rag_use_qdrant=True, llm_provider="mock"),
    )

    results = service.retrieve("白灼虾怎么处理安全？", top_k=3)

    assert results[0].chunk_type == ChunkType.SAFETY
    assert results[1].chunk_type == ChunkType.STEP


def test_rag_retrieve_prefers_substitution_for_missing_ingredient_questions() -> None:
    """Verify missing-ingredient questions prefer substitution chunks."""
    chunks = [
        _chunk(ChunkType.STEP, score=0.95),
        _chunk(ChunkType.INGREDIENTS, score=0.80),
        _chunk(ChunkType.SUBSTITUTION, score=0.65),
    ]

    class _WorkingQdrantStore:
        """Store that returns intentionally unsorted semantic chunks."""

        def search(self, query: str, top_k: int):
            """Return the prepared chunks."""
            return chunks

    service = RAGService(
        qdrant_store=_WorkingQdrantStore(),
        settings=Settings(_env_file=None, rag_use_qdrant=True, llm_provider="mock"),
    )

    results = service.retrieve("没有蚝油怎么办？", top_k=3)

    assert results[0].chunk_type == ChunkType.SUBSTITUTION
    assert results[1].chunk_type == ChunkType.INGREDIENTS


def _chunk(chunk_type: ChunkType, *, score: float) -> SourceChunk:
    """Build a minimal source chunk for rerank tests."""
    return SourceChunk(
        recipe_id=1,
        recipe_name="测试菜",
        chunk_type=chunk_type,
        content=f"测试内容：{chunk_type}",
        score=score,
        metadata={"retrieval_source": "qdrant"},
    )
