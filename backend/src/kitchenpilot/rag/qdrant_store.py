from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from kitchenpilot.core.config import Settings, get_settings
from kitchenpilot.core.embeddings import EmbeddingProvider, build_embedding_provider
from kitchenpilot.rag.chunks import build_recipe_chunks
from kitchenpilot.schemas.enums import ChunkType
from kitchenpilot.schemas.recipe import SourceChunk
from kitchenpilot.services.recipe_service import RecipeService


def chunk_point_id(chunk: SourceChunk) -> str:
    """Return a stable Qdrant point id for a source chunk."""
    chunk_id = str(chunk.metadata.get("chunk_id") or f"recipe:{chunk.recipe_id}:{chunk.chunk_type}")
    return str(uuid5(NAMESPACE_URL, chunk_id))


def chunk_payload(chunk: SourceChunk) -> dict[str, object]:
    """Build the Qdrant payload stored alongside a chunk vector."""
    return {
        "recipe_id": chunk.recipe_id,
        "recipe_name": chunk.recipe_name,
        "chunk_type": chunk.chunk_type.value,
        "content": chunk.content,
        "metadata": chunk.metadata,
    }


def chunk_to_point(chunk: SourceChunk, vector: list[float]) -> PointStruct:
    """Convert one source chunk and vector into a Qdrant point."""
    return PointStruct(
        id=chunk_point_id(chunk),
        vector=vector,
        payload=chunk_payload(chunk),
    )


def source_chunk_from_payload(payload: dict[str, object], score: float = 0.0) -> SourceChunk:
    """Convert a Qdrant payload back into the public SourceChunk schema."""
    metadata = payload.get("metadata", {})
    metadata = metadata.copy() if isinstance(metadata, dict) else {}
    metadata["retrieval_source"] = "qdrant"
    return SourceChunk(
        recipe_id=int(payload["recipe_id"]),
        recipe_name=str(payload["recipe_name"]),
        chunk_type=ChunkType(str(payload["chunk_type"])),
        content=str(payload["content"]),
        score=score,
        metadata=metadata,
    )


class QdrantRecipeStore:
    """Store and retrieve recipe chunks from Qdrant."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: QdrantClient | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        collection_name: str | None = None,
    ) -> None:
        """Initialize this store with Qdrant and embedding collaborators."""
        self.settings = settings or get_settings()
        self.client = client or QdrantClient(
            url=self.settings.qdrant_url,
            api_key=self.settings.qdrant_api_key or None,
            timeout=self.settings.qdrant_timeout,
        )
        self.embedding_provider = embedding_provider or build_embedding_provider(self.settings)
        self.collection_name = collection_name or self.settings.qdrant_collection

    def ensure_collection(self, vector_size: int | None = None) -> None:
        """Create the configured collection when it does not already exist."""
        if self.client.collection_exists(self.collection_name):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=vector_size or self.settings.qdrant_vector_size,
                distance=Distance.COSINE,
            ),
        )

    def upsert_chunks(self, chunks: list[SourceChunk], batch_size: int = 32) -> int:
        """Embed and upsert source chunks into Qdrant."""
        if not chunks:
            return 0

        total = 0
        first_vector_size: int | None = None
        for index in range(0, len(chunks), batch_size):
            batch = chunks[index : index + batch_size]
            vectors = self.embedding_provider.embed([chunk.content for chunk in batch])
            if first_vector_size is None and vectors:
                first_vector_size = len(vectors[0])
                self.ensure_collection(first_vector_size)
            points = [chunk_to_point(chunk, vector) for chunk, vector in zip(batch, vectors, strict=True)]
            self.client.upsert(collection_name=self.collection_name, points=points)
            total += len(points)
        return total

    def search(self, query: str, top_k: int = 4) -> list[SourceChunk]:
        """Search Qdrant for recipe chunks relevant to a query."""
        vectors = self.embedding_provider.embed([query])
        if not vectors:
            return []
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=vectors[0],
            limit=top_k,
            with_payload=True,
        )
        results = getattr(response, "points", response)
        chunks: list[SourceChunk] = []
        for result in results:
            payload = result.payload or {}
            if isinstance(payload, dict):
                chunks.append(source_chunk_from_payload(payload, score=float(result.score)))
        return chunks


def seed_qdrant(
    *,
    recipe_service: RecipeService | None = None,
    store: QdrantRecipeStore | None = None,
    batch_size: int = 32,
) -> dict[str, int]:
    """Generate recipe chunks and upsert them into Qdrant."""
    recipe_service = recipe_service or RecipeService()
    chunks = build_recipe_chunks(recipe_service.list_recipes())
    store = store or QdrantRecipeStore()
    upserted = store.upsert_chunks(chunks, batch_size=batch_size)
    return {"chunks": len(chunks), "upserted": upserted}
