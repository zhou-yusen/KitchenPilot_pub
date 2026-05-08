from kitchenpilot.core.config import get_settings
from kitchenpilot.core.llm import ChatMessage, OpenAICompatibleChatProvider


EXIT_COMMANDS = {"/exit", "/quit", "exit", "quit", "q"}


def build_openai_compatible_provider() -> OpenAICompatibleChatProvider:
    """Build an OpenAI-compatible chat provider from project environment settings."""
    settings = get_settings()
    return OpenAICompatibleChatProvider(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        timeout=settings.llm_timeout,
        disable_thinking=settings.openai_disable_thinking,
        trust_env=settings.openai_trust_env,
    )


def main() -> None:
    """Start a minimal terminal chat loop against an OpenAI-compatible endpoint."""
    settings = get_settings()
    provider = build_openai_compatible_provider()
    messages = [
        ChatMessage(
            role="system",
            content="你是 KitchenPilot 的做菜助手。请直接回答，不要输出思考过程。",
        )
    ]

    print("KitchenPilot OpenAI-compatible chat")
    print(f"Base URL: {settings.openai_base_url}")
    print(f"Chat model: {settings.openai_model}")
    print(f"Reasoning disabled: {settings.openai_disable_thinking}")
    print(f"Trust environment proxy: {settings.openai_trust_env}")
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
        print(f"\nLLM: {answer}")


if __name__ == "__main__":
    main()
