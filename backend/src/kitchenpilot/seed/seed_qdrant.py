"""Seed recipe chunks into Qdrant, with optional chunk dump to JSON."""

import argparse
import json
from pathlib import Path

from kitchenpilot.rag.chunks import build_recipe_chunks
from kitchenpilot.rag.qdrant_store import QdrantRecipeStore
from kitchenpilot.services.recipe_service import RecipeService

SPLIT_COLLECTION_SUFFIX = "_split"
MERGED_COLLECTION_SUFFIX = "_merged"


def _dump_chunks(chunks, path: Path) -> None:
    """Write chunks to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for c in chunks:
        rows.append({
            "recipe_id": c.recipe_id,
            "recipe_name": c.recipe_name,
            "chunk_type": getattr(c.chunk_type, "value", str(c.chunk_type)),
            "content": c.content,
            "metadata": {k: str(v) for k, v in c.metadata.items()},
        })
    path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Dumped {len(rows)} chunks to: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed recipe chunks into Qdrant.")
    parser.add_argument(
        "--dump-chunks",
        type=Path,
        default=None,
        help="Dump generated chunks to a JSON file before upserting.",
    )
    parser.add_argument(
        "--dump-both",
        action="store_true",
        help="Dump both split and merged chunk versions to JSON.",
    )
    parser.add_argument(
        "--seed-both",
        action="store_true",
        help="Seed both split and merged collections into Qdrant.",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Use merged chunk strategy (default: split). Ignored when --seed-both.",
    )
    args = parser.parse_args()

    recipe_service = RecipeService()
    recipes = recipe_service.list_recipes()

    # ── Dump chunks to JSON ──────────────────────────────────────────────
    if args.dump_both:
        dump_dir = args.dump_chunks or Path("backend/src/kitchenpilot/seed/data")
        split_chunks = build_recipe_chunks(recipes, merge=False)
        merged_chunks = build_recipe_chunks(recipes, merge=True)
        print(f"Split chunks: {len(split_chunks)}")
        print(f"Merged chunks: {len(merged_chunks)}")
        _dump_chunks(split_chunks, Path(dump_dir) / "chunks_split.json")
        _dump_chunks(merged_chunks, Path(dump_dir) / "chunks_merged.json")
    elif args.dump_chunks:
        chunks = build_recipe_chunks(recipes, merge=args.merge)
        print(f"Generated chunks: {len(chunks)}")
        _dump_chunks(chunks, args.dump_chunks)

    # ── Seed Qdrant ──────────────────────────────────────────────────────
    if args.seed_both:
        base_collection = QdrantRecipeStore().collection_name

        for suffix, merge_flag in [
            (SPLIT_COLLECTION_SUFFIX, False),
            (MERGED_COLLECTION_SUFFIX, True),
        ]:
            collection = f"{base_collection}{suffix}"
            chunks = build_recipe_chunks(recipes, merge=merge_flag)
            store = QdrantRecipeStore(collection_name=collection)
            upserted = store.upsert_chunks(chunks)
            strategy = "merged" if merge_flag else "split"
            print(f"[{strategy}] collection={collection}  chunks={len(chunks)}  upserted={upserted}")
    else:
        chunks = build_recipe_chunks(recipes, merge=args.merge)
        if not args.dump_chunks and not args.dump_both:
            print(f"Generated chunks: {len(chunks)}")
        store = QdrantRecipeStore()
        upserted = store.upsert_chunks(chunks)
        print(f"Upserted chunks: {upserted}")


if __name__ == "__main__":
    main()
