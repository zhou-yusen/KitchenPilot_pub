from collections import Counter

from kitchenpilot.rag.chunks import build_recipe_chunks
from kitchenpilot.services.recipe_service import RecipeService


def main() -> None:
    """Print a terminal preview of generated recipe chunks."""
    recipes = RecipeService().list_recipes()
    chunks = build_recipe_chunks(recipes)
    counts = Counter(chunk.chunk_type for chunk in chunks)

    print("KitchenPilot Recipe Chunk Preview")
    print("=" * 40)
    print(f"Recipes: {len(recipes)}")
    print(f"Chunks: {len(chunks)}")
    print()
    print("By chunk type:")
    for chunk_type, count in sorted(counts.items(), key=lambda item: item[0]):
        print(f"  {chunk_type}: {count}")

    print()
    print("Sample chunks:")
    for chunk in chunks[:8]:
        chunk_id = chunk.metadata.get("chunk_id", "")
        print("-" * 40)
        print(f"id: {chunk_id}")
        print(f"recipe: {chunk.recipe_name}")
        print(f"type: {chunk.chunk_type}")
        print("content:")
        for line in chunk.content.splitlines():
            print(f"  {line}")


if __name__ == "__main__":
    main()
