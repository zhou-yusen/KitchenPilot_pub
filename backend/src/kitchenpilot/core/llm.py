from typing import Protocol

from pydantic import BaseModel, Field

from kitchenpilot.core.config import Settings, get_settings
from kitchenpilot.core.http import auth_headers, post_json


class ChatMessage(BaseModel):
    """Represent one message sent to or returned from a chat model."""

    role: str
    content: str


class ChatResult(BaseModel):
    """Represent the final content and raw provider response for one chat call."""

    content: str
    raw: dict[str, object] = Field(default_factory=dict)


class ChatProvider(Protocol):
    """Define the chat operation required by answer generation."""

    def chat(self, messages: list[ChatMessage]) -> ChatResult:
        """Generate a chat response from a list of messages."""
        ...


class MockChatProvider:
    """Provide deterministic chat responses for tests that should not call a real model."""

    def chat(self, messages: list[ChatMessage]) -> ChatResult:
        """Return a predictable answer based on the last user message."""
        prompt = messages[-1].content if messages else ""
        return ChatResult(content=f"Mock answer: {prompt}")


class OllamaChatProvider:
    """Call local Ollama /api/chat without reading proxy settings."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout: float,
        disable_thinking: bool = True,
        trust_env: bool = False,
    ) -> None:
        """Initialize this chat provider with its model and HTTP behavior."""
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.disable_thinking = disable_thinking
        self.trust_env = trust_env

    def chat(self, messages: list[ChatMessage]) -> ChatResult:
        """Call Ollama /api/chat and return only the final assistant content."""
        payload = {
            "model": self.model,
            "messages": [message.model_dump() for message in messages],
            "stream": False,
        }
        if self.disable_thinking:
            payload["think"] = False

        data = post_json(
            f"{self.base_url}/api/chat",
            payload,
            timeout=self.timeout,
            trust_env=self.trust_env,
        )
        message = data.get("message", {})
        content = message.get("content", "") if isinstance(message, dict) else ""
        return ChatResult(content=str(content).strip(), raw=data)


class OpenAICompatibleChatProvider:
    """Call /chat/completions endpoints that follow the OpenAI HTTP API shape."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float,
        disable_thinking: bool = True,
        trust_env: bool = True,
    ) -> None:
        """Initialize this chat provider with OpenAI-compatible endpoint settings."""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.disable_thinking = disable_thinking
        self.trust_env = trust_env

    def chat(self, messages: list[ChatMessage]) -> ChatResult:
        """Call /chat/completions and return the first assistant message content."""
        payload = {
            "model": self.model,
            "messages": [message.model_dump() for message in messages],
            "stream": False,
        }
        if self.disable_thinking:
            payload["reasoning_effort"] = "none"

        data = post_json(
            f"{self.base_url}/chat/completions",
            payload,
            headers=auth_headers(self.api_key),
            timeout=self.timeout,
            trust_env=self.trust_env,
        )
        choices = data.get("choices", [])
        message: dict[str, object] = {}
        if choices and isinstance(choices, list) and isinstance(choices[0], dict):
            raw_message = choices[0].get("message", {})
            if isinstance(raw_message, dict):
                message = raw_message
        content = message.get("content", "")
        return ChatResult(content=str(content).strip(), raw=data)


class MiMoChatProvider:
    """Call Xiaomi MiMo through its OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float,
        disable_thinking: bool = True,
        trust_env: bool = True,
    ) -> None:
        """Initialize this chat provider with MiMo endpoint settings."""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.disable_thinking = disable_thinking
        self.trust_env = trust_env

    def chat(self, messages: list[ChatMessage]) -> ChatResult:
        """Call MiMo chat completions and return the first assistant content."""
        payload = {
            "model": self.model,
            "messages": [message.model_dump() for message in messages],
            "stream": False,
        }
        if self.disable_thinking:
            payload["thinking"] = {"type": "disabled"}

        data = post_json(
            f"{self.base_url}/chat/completions",
            payload,
            headers=auth_headers(self.api_key),
            timeout=self.timeout,
            trust_env=self.trust_env,
        )
        choices = data.get("choices", [])
        message: dict[str, object] = {}
        if choices and isinstance(choices, list) and isinstance(choices[0], dict):
            raw_message = choices[0].get("message", {})
            if isinstance(raw_message, dict):
                message = raw_message
        content = message.get("content", "")
        return ChatResult(content=str(content).strip(), raw=data)


def build_chat_provider(settings: Settings | None = None) -> ChatProvider:
    """Build the configured chat provider."""
    settings = settings or get_settings()
    if settings.llm_provider == "mock":
        return MockChatProvider()
    if settings.llm_provider == "ollama":
        return OllamaChatProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.llm_timeout,
            disable_thinking=settings.ollama_disable_thinking,
            trust_env=settings.ollama_trust_env,
        )
    if settings.llm_provider == "openai":
        return OpenAICompatibleChatProvider(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout=settings.llm_timeout,
            disable_thinking=settings.openai_disable_thinking,
            trust_env=settings.openai_trust_env,
        )
    if settings.llm_provider == "mimo":
        return MiMoChatProvider(
            base_url=settings.mimo_base_url,
            api_key=settings.mimo_api_key,
            model=settings.mimo_model,
            timeout=settings.llm_timeout,
            disable_thinking=settings.mimo_disable_thinking,
            trust_env=settings.mimo_trust_env,
        )
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")


def build_chat_model(settings: Settings) -> ChatProvider:
    """Keep the older factory name as a compatibility alias for chat only."""
    return build_chat_provider(settings)
