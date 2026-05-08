from collections import Counter

from kitchenpilot.rag.chunks import build_recipe_chunks
from kitchenpilot.schemas.enums import ChunkType
from kitchenpilot.services.recipe_service import RecipeService


def test_build_recipe_chunks_creates_expected_semantic_types() -> None:
    """Verify chunk generation produces all semantic chunk categories."""
    recipe = RecipeService().list_recipes()[0]

    chunks = build_recipe_chunks([recipe])

    counts = Counter(chunk.chunk_type for chunk in chunks)
    assert counts[ChunkType.OVERVIEW] == 1
    assert counts[ChunkType.INGREDIENTS] == 1
    assert counts[ChunkType.STEP] == len(recipe.steps)
    assert counts[ChunkType.FAILURE] == len(recipe.common_failures)
    assert counts[ChunkType.SUBSTITUTION] == len(recipe.substitutions)
    assert counts[ChunkType.SAFETY] == len(recipe.safety_notes)


def test_build_recipe_chunks_adds_stable_vector_metadata() -> None:
    """Verify chunks include metadata needed for Qdrant upsert and filtering."""
    recipe = RecipeService().list_recipes()[0]

    chunk = build_recipe_chunks([recipe])[0]

    assert chunk.metadata["chunk_id"]
    assert chunk.metadata["content_hash"]
    assert chunk.metadata["schema_version"] == 1
    assert chunk.metadata["ingredients"]
    assert chunk.metadata["difficulty"] == recipe.difficulty
    assert chunk.metadata["beginner_friendly"] == recipe.beginner_friendly
    assert chunk.metadata["time_minutes"] == recipe.time_minutes
