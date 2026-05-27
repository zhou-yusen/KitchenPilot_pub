import argparse

from kitchenpilot.agent.nodes.intent_router import IntentRouter
from kitchenpilot.core.config import get_settings
from kitchenpilot.core.embeddings import build_embedding_provider

DEFAULT_QUERIES = [
    "土豆丝怎么炒得脆？",
    "我有鸡蛋、番茄和米饭，推荐一道简单菜。",
    "想按我的偏好安排一顿晚饭",
    "今晚想吃清淡点，别太麻烦",
    "随便帮我想想",
]

EXIT_COMMANDS = {"/exit", "/quit", "exit", "quit", "q"}


def print_settings() -> None:
    """Print the LLM and embedding settings used by this demo."""
    settings = get_settings()
    print("KitchenPilot intent router demo")
    print("=" * 34)
    print(f"LLM provider: {settings.llm_provider}")
    if settings.llm_provider == "openai":
        print(f"OpenAI-compatible base URL: {settings.openai_base_url}")
        print(f"OpenAI-compatible chat model: {settings.openai_model}")
        print(f"OpenAI-compatible trust env proxy: {settings.openai_trust_env}")
    elif settings.llm_provider == "mimo":
        print(f"MiMo base URL: {settings.mimo_base_url}")
        print(f"MiMo chat model: {settings.mimo_model}")
        print(f"MiMo trust env proxy: {settings.mimo_trust_env}")
    elif settings.llm_provider == "ollama":
        print(f"Ollama base URL: {settings.ollama_base_url}")
        print(f"Ollama chat model: {settings.ollama_model}")
        print(f"Ollama trust env proxy: {settings.ollama_trust_env}")
    print(f"Embedding provider: {settings.resolved_embedding_provider}")
    if settings.resolved_embedding_provider == "openai":
        print(f"OpenAI-compatible embedding model: {settings.openai_embedding_model}")
    elif settings.resolved_embedding_provider == "ollama":
        print(f"Ollama embedding model: {settings.ollama_embedding_model}")
    print()


def check_provider() -> None:
    """Run a small embedding probe so provider configuration errors are visible."""
    provider = build_embedding_provider()
    try:
        embeddings = provider.embed(["intent router probe"])
    except Exception as exc:
        print(f"Embedding probe: FAILED ({exc})")
        print("Router will fall back to keyword rules unless LLM fallback succeeds.")
        print()
        return

    vector_size = len(embeddings[0]) if embeddings else 0
    print(f"Embedding probe: OK (vector size={vector_size})")
    print()


def show_result(router: IntentRouter, query: str) -> None:
    """Classify one query and print the routing result."""
    result = router.classify_with_confidence(query)
    print(f"Query: {query}")
    print(f"  intent: {result.intent}")
    print(f"  confidence: {result.confidence:.2f}")
    print(f"  source: {result.source}")
    print(f"  ingredients: {result.ingredients or []}")
    print(f"  needs_clarification: {result.needs_clarification}")
    if result.needs_clarification and result.clarification_question:
        print("  clarification_question:")
        for line in result.clarification_question.splitlines():
            print(f"    {line}")
    print()


def run_examples(router: IntentRouter, queries: list[str]) -> None:
    """Run a fixed list of sample queries through the router."""
    print("Sample queries")
    print("-" * 34)
    for query in queries:
        show_result(router, query)


def run_interactive(router: IntentRouter) -> None:
    """Run an interactive terminal loop for ad-hoc intent routing checks."""
    print("Interactive mode. Type /exit to stop.")
    while True:
        query = input("\nQuery: ").strip()
        if not query:
            continue
        if query.lower() in EXIT_COMMANDS:
            break
        show_result(router, query)


def main() -> None:
    """Run the intent router demo from the command line."""
    parser = argparse.ArgumentParser(description="Demo KitchenPilot intent routing.")
    parser.add_argument(
        "--query",
        action="append",
        help="Custom query to classify. Can be passed multiple times.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Keep reading queries from the terminal after sample output.",
    )
    args = parser.parse_args()

    router = IntentRouter()
    queries = args.query or DEFAULT_QUERIES

    print_settings()
    check_provider()
    run_examples(router, queries)
    if args.interactive:
        run_interactive(router)


if __name__ == "__main__":
    main()
