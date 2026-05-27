from kitchenpilot.core.config import get_settings
from kitchenpilot.core.llm import ChatMessage, MiMoChatProvider

EXIT_COMMANDS = {"/exit", "/quit", "exit", "quit", "q"}


def build_mimo_provider() -> MiMoChatProvider:
    """Build a Xiaomi MiMo chat provider from project environment settings."""
    settings = get_settings()
    return MiMoChatProvider(
        base_url=settings.mimo_base_url,
        api_key=settings.mimo_api_key,
        model=settings.mimo_model,
        timeout=settings.llm_timeout,
        disable_thinking=settings.mimo_disable_thinking,
        trust_env=settings.mimo_trust_env,
    )


def main() -> None:
    """Start a minimal terminal chat loop against Xiaomi MiMo."""
    settings = get_settings()
    provider = build_mimo_provider()
    messages = [
        ChatMessage(
            role="system",
            content="你是 KitchenPilot 的做菜助手。请直接回答，不要输出思考过程。",
        )
    ]

    print("KitchenPilot Xiaomi MiMo chat")
    print("Chat provider: mimo")
    print(f"Base URL: {settings.mimo_base_url}")
    print(f"Chat model: {settings.mimo_model}")
    print(f"Thinking disabled: {settings.mimo_disable_thinking}")
    print(f"Trust environment proxy: {settings.mimo_trust_env}")
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
            print(f"MiMo 调用失败: {exc}")
            continue

        answer = result.content or "(空响应)"
        messages.append(ChatMessage(role="assistant", content=answer))
        print(f"\nMiMo: {answer}")


if __name__ == "__main__":
    main()
