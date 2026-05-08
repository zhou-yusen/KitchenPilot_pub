from kitchenpilot.core.config import Settings
from kitchenpilot.core.embeddings import MockEmbeddingProvider
from kitchenpilot.rag.chunks import build_recipe_chunks
from kitchenpilot.rag.qdrant_store import QdrantRecipeStore, chunk_to_point, seed_qdrant
from kitchenpilot.services.recipe_service import RecipeService


class _FakeQdrantClient:
    """Minimal fake Qdrant client for seed tests."""

    def __init__(self) -> None:
        """Initialize captured calls."""
        self.created: list[tuple[str, object]] = []
        self.upserted: list[object] = []

    def collection_exists(self, collection_name: str) -> bool:
        """Pretend the collection does not exist yet."""
        return bool(self.created)

    def create_collection(self, collection_name: str, vectors_config: object) -> None:
        """Capture collection creation."""
        self.created.append((collection_name, vectors_config))

    def upsert(self, collection_name: str, points: list[object]) -> None:
        """Capture upserted points."""
        self.upserted.extend(points)


class _OneRecipeService:
    """Recipe service returning one recipe for deterministic seed tests."""

    def list_recipes(self):
        """Return one available recipe."""
        return RecipeService().list_recipes()[:1]


def test_chunk_to_point_preserves_payload_for_qdrant() -> None:
    """Verify a chunk is converted to a Qdrant point with expected payload."""
    chunk = build_recipe_chunks(RecipeService().list_recipes()[:1])[0]

    point = chunk_to_point(chunk, [0.1, 0.2, 0.3])

    assert point.id
    assert point.vector == [0.1, 0.2, 0.3]
    assert point.payload["recipe_id"] == chunk.recipe_id
    assert point.payload["recipe_name"] == chunk.recipe_name
    assert point.payload["chunk_type"] == chunk.chunk_type.value
    assert point.payload["content"] == chunk.content
    assert point.payload["metadata"]["chunk_id"] == chunk.metadata["chunk_id"]


def test_seed_qdrant_uses_embedding_provider_and_upserts_points() -> None:
    """Verify seed_qdrant embeds generated chunks and upserts them into Qdrant."""
    settings = Settings(_env_file=None, qdrant_collection="test_chunks", qdrant_vector_size=2)
    client = _FakeQdrantClient()
    store = QdrantRecipeStore(
        settings=settings,
        client=client,
        embedding_provider=MockEmbeddingProvider(),
    )

    result = seed_qdrant(recipe_service=_OneRecipeService(), store=store, batch_size=8)

    assert result["chunks"] == result["upserted"]
    assert result["upserted"] == len(client.upserted)
    assert client.created[0][0] == "test_chunks"
