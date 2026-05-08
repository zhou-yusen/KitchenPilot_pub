from kitchenpilot.core.config import get_settings
from kitchenpilot.core.llm import ChatMessage, OllamaChatProvider


EXIT_COMMANDS = {"/exit", "/quit", "exit", "quit", "q"}


def build_ollama_provider() -> OllamaChatProvider:
    """Build an Ollama chat provider from project environment settings."""
    settings = get_settings()
    return OllamaChatProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout=settings.llm_timeout,
        disable_thinking=settings.ollama_disable_thinking,
        trust_env=settings.ollama_trust_env,
    )


def main() -> None:
    """Start a minimal terminal chat loop against local Ollama."""
    settings = get_settings()
    provider = build_ollama_provider()
    messages = [
        ChatMessage(
            role="system",
            content="你是 KitchenPilot 的本地做菜助手。请直接回答，不要输出思考过程。",
        )
    ]

    print("KitchenPilot Ollama chat")
    print(f"Base URL: {settings.ollama_base_url}")
    print(f"Chat model: {settings.ollama_model}")
    print(f"Thinking disabled: {settings.ollama_disable_thinking}")
    print(f"Trust environment proxy: {settings.ollama_trust_env}")
    print("输入 /exit 结束。")

    while True:
        query = input("\n你: ").strip()
        if not query:
            continue
        if query.lower() in EXIT_COMMANDS:
            break

        messages.append(ChatMessage(role="user", content=query))
        try:
            result = provider.chat(messages)
        except Exception as exc:
            print(f"LLM 调用失败: {exc}")
            continue

        answer = result.content or "(空响应)"
        messages.append(ChatMessage(role="assistant", content=answer))
        print(f"\nOllama: {answer}")


if __name__ == "__main__":
    main()
