from kitchenpilot.rag.qdrant_store import seed_qdrant


def main() -> None:
    """Seed generated recipe chunks into Qdrant."""
    result = seed_qdrant()
    print(f"Generated chunks: {result['chunks']}")
    print(f"Upserted chunks: {result['upserted']}")


if __name__ == "__main__":
    main()
