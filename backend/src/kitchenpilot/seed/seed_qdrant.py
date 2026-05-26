"""Seed recipe chunks into Qdrant, with optional chunk dump to JSON."""

import argparse
import json
from pathlib import Path

from kitchenpilot.rag.chunks import build_recipe_chunks
from kitchenpilot.rag.qdrant_store import QdrantRecipeStore
from kitchenpilot.services.recipe_service import RecipeService


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed recipe chunks into Qdrant.")
    parser.add_argument(
        "--dump-chunks",
        type=Path,
        default=None,
        help="Dump generated chunks to a JSON file before upserting.",
    )
    args = parser.parse_args()

    recipe_service = RecipeService()
    recipes = recipe_service.list_recipes()
    chunks = build_recipe_chunks(recipes)

    print(f"Generated chunks: {len(chunks)}")

    # Optionally dump chunks to JSON
    if args.dump_chunks:
        args.dump_chunks.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for c in chunks:
            rows.append({
                "recipe_id": c.recipe_id,
                "recipe_name": c.recipe_name,
                "chunk_type": getattr(c.chunk_type, "value", str(c.chunk_type)),
                "content": c.content,
                "metadata": {k: str(v) for k, v in c.metadata.items()},
            })
        args.dump_chunks.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Dumped chunks to: {args.dump_chunks}")

    # Upsert to Qdrant
    store = QdrantRecipeStore()
    upserted = store.upsert_chunks(chunks)
    print(f"Upserted chunks: {upserted}")


if __name__ == "__main__":
    main()
