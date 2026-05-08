from kitchenpilot.core.config import get_settings
from kitchenpilot.rag.chunks import build_recipe_chunks
from kitchenpilot.services.recipe_service import RecipeService


def seed_qdrant_placeholder() -> list[dict[str, object]]:
    """Return chunk payloads that will be embedded and written to Qdrant in phase 3."""
    settings = get_settings()
    chunks = build_recipe_chunks(RecipeService().list_recipes())
    return [
        {
            "collection": settings.qdrant_collection,
            "recipe_id": chunk.recipe_id,
            "recipe_name": chunk.recipe_name,
            "chunk_type": chunk.chunk_type,
            "content": chunk.content,
            "metadata": chunk.metadata,
        }
        for chunk in chunks
    ]


if __name__ == "__main__":
    for payload in seed_qdrant_placeholder():
        print(payload)

