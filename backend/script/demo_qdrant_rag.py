import argparse

from kitchenpilot.core.config import get_settings
from kitchenpilot.core.embeddings import build_embedding_provider
from kitchenpilot.rag.chunks import build_recipe_chunks
from kitchenpilot.rag.qdrant_store import QdrantRecipeStore, seed_qdrant
from kitchenpilot.rag.service import RAGService
from kitchenpilot.services.recipe_service import RecipeService


DEFAULT_QUERIES = [
    "土豆丝怎么炒得脆？",
    "没有蚝油怎么办？",
    "鸡翅为什么有腥味？",
    "白灼虾怎么处理安全？",
]


def main() -> None:
    """Run a small Qdrant RAG demo from the terminal."""
    parser = argparse.ArgumentParser(description="Demo KitchenPilot Qdrant RAG retrieval.")
    parser.add_argument("--query", action="append", help="Custom query. Can be repeated.")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--seed", action="store_true", help="Upsert chunks into Qdrant first.")
    args = parser.parse_args()

    settings = get_settings()
    recipes = RecipeService().list_recipes()
    chunks = build_recipe_chunks(recipes)

    print("KitchenPilot Qdrant RAG demo")
    print("=" * 40)
    print(f"Recipes: {len(recipes)}")
    print(f"Chunks: {len(chunks)}")
    print(f"Qdrant URL: {settings.qdrant_url}")
    print(f"Qdrant collection: {settings.qdrant_collection}")
    print(f"RAG use Qdrant: {settings.rag_use_qdrant}")

    try:
        embeddings = build_embedding_provider(settings).embed(["qdrant rag probe"])
        print(f"Embedding probe: OK (vector size={len(embeddings[0]) if embeddings else 0})")
    except Exception as exc:
        print(f"Embedding probe: FAILED ({exc})")

    if args.seed:
        try:
            result = seed_qdrant(batch_size=32)
            print(f"Seed: OK (chunks={result['chunks']}, upserted={result['upserted']})")
        except Exception as exc:
            print(f"Seed: FAILED ({exc})")

    try:
        store = QdrantRecipeStore(settings=settings)
        exists = store.client.collection_exists(settings.qdrant_collection)
        print(f"Qdrant collection exists: {exists}")
    except Exception as exc:
        print(f"Qdrant probe: FAILED ({exc})")

    service = RAGService(settings=settings)
    queries = args.query or DEFAULT_QUERIES
    for query in queries:
        print()
        print("-" * 40)
        print(f"Query: {query}")
        results = service.retrieve(query, top_k=args.top_k)
        for index, chunk in enumerate(results, start=1):
            source = chunk.metadata.get("retrieval_source", "qdrant")
            print(
                f"{index}. {chunk.recipe_name} | {chunk.chunk_type} | "
                f"score={chunk.score:.4f} | source={source}"
            )
            first_line = chunk.content.splitlines()[0] if chunk.content else ""
            print(f"   {first_line}")


if __name__ == "__main__":
    main()
