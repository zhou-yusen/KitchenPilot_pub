from typing import Any

from kitchenpilot.core.config import Settings


def build_chat_model(settings: Settings) -> Any:
    """Build a LangChain chat model using official integrations."""
    if settings.llm_provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("Install langchain-ollama to use Ollama models.") from exc

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("Install langchain-openai to use OpenAI models.") from exc

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )

