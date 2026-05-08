from kitchenpilot.core.config import Settings
from kitchenpilot.core.embeddings import (
    OllamaEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    build_embedding_provider,
)
from kitchenpilot.core.llm import (
    ChatMessage,
    OllamaChatProvider,
    OpenAICompatibleChatProvider,
    build_chat_provider,
)


class _FakeResponse:
    """Minimal response object used to test provider request handling."""

    def __init__(self, payload: dict[str, object]) -> None:
        """Store the fake JSON payload."""
        self.payload = payload

    def raise_for_status(self) -> None:
        """Match the httpx response API without raising."""

    def json(self) -> dict[str, object]:
        """Return the configured JSON payload."""
        return self.payload


class _FakeClient:
    """Capture provider requests without opening a network connection."""

    instances: list["_FakeClient"] = []

    def __init__(self, *, timeout: float, trust_env: bool) -> None:
        """Record constructor arguments from the provider."""
        self.timeout = timeout
        self.trust_env = trust_env
        self.requests: list[tuple[str, dict[str, object], dict[str, str] | None]] = []
        self.instances.append(self)

    def __enter__(self) -> "_FakeClient":
        """Return the fake client for context manager usage."""
        return self

    def __exit__(self, *args: object) -> None:
        """Match the httpx client context manager API."""

    def post(
        self,
        url: str,
        json: dict[str, object],
        headers: dict[str, str] | None = None,
    ) -> _FakeResponse:
        """Record the request and return a response matching the endpoint."""
        self.requests.append((url, json, headers))
        if url.endswith("/api/embed"):
            return _FakeResponse({"embeddings": [[1, 2, 3]]})
        if url.endswith("/v1/chat/completions"):
            return _FakeResponse({"choices": [{"message": {"content": "openai ok"}}]})
        if url.endswith("/v1/embeddings"):
            return _FakeResponse({"data": [{"embedding": [4, 5, 6]}]})
        return _FakeResponse({"message": {"content": "ok"}})


def test_ollama_chat_disables_thinking_and_ignores_proxy(monkeypatch) -> None:
    """Verify local Ollama chat requests disable thinking and environment proxy usage."""
    _FakeClient.instances = []
    monkeypatch.setattr("kitchenpilot.core.http.httpx.Client", _FakeClient)
    provider = OllamaChatProvider(
        base_url="http://localhost:11434",
        model="qwen3.5:4b",
        timeout=12,
        disable_thinking=True,
        trust_env=False,
    )

    result = provider.chat([ChatMessage(role="user", content="番茄炒蛋怎么做？")])

    client = _FakeClient.instances[0]
    assert result.content == "ok"
    assert client.timeout == 12
    assert client.trust_env is False
    assert client.requests[0][0] == "http://localhost:11434/api/chat"
    assert client.requests[0][1]["model"] == "qwen3.5:4b"
    assert client.requests[0][1]["think"] is False


def test_ollama_embedding_uses_configured_embedding_model(monkeypatch) -> None:
    """Verify Ollama embedding requests use the qwen embedding model."""
    _FakeClient.instances = []
    monkeypatch.setattr("kitchenpilot.core.http.httpx.Client", _FakeClient)
    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="qwen3-embedding:0.6b",
        timeout=12,
        trust_env=False,
    )

    embeddings = provider.embed(["番茄炒蛋"])

    client = _FakeClient.instances[0]
    assert embeddings == [[1.0, 2.0, 3.0]]
    assert client.requests[0][0] == "http://localhost:11434/api/embed"
    assert client.requests[0][1]["model"] == "qwen3-embedding:0.6b"


def test_openai_compatible_chat_uses_standard_endpoint_and_reasoning_off(monkeypatch) -> None:
    """Verify OpenAI-compatible chat requests can disable thinking models."""
    _FakeClient.instances = []
    monkeypatch.setattr("kitchenpilot.core.http.httpx.Client", _FakeClient)
    provider = OpenAICompatibleChatProvider(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        model="qwen3.5:4b",
        timeout=12,
        disable_thinking=True,
        trust_env=False,
    )

    result = provider.chat([ChatMessage(role="user", content="番茄炒蛋怎么做？")])

    client = _FakeClient.instances[0]
    assert result.content == "openai ok"
    assert client.trust_env is False
    assert client.requests[0][0] == "http://localhost:11434/v1/chat/completions"
    assert client.requests[0][1]["model"] == "qwen3.5:4b"
    assert client.requests[0][1]["reasoning_effort"] == "none"
    assert client.requests[0][2]["Authorization"] == "Bearer ollama"


def test_openai_compatible_embedding_uses_standard_embeddings_endpoint(monkeypatch) -> None:
    """Verify OpenAI-compatible embedding requests use /embeddings."""
    _FakeClient.instances = []
    monkeypatch.setattr("kitchenpilot.core.http.httpx.Client", _FakeClient)
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        model="qwen3-embedding:0.6b",
        timeout=12,
        trust_env=False,
    )

    embeddings = provider.embed(["番茄炒蛋"])

    client = _FakeClient.instances[0]
    assert embeddings == [[4.0, 5.0, 6.0]]
    assert client.requests[0][0] == "http://localhost:11434/v1/embeddings"
    assert client.requests[0][1]["model"] == "qwen3-embedding:0.6b"


def test_build_factories_use_project_ollama_defaults() -> None:
    """Verify separate factories build the requested local Ollama providers."""
    settings = Settings(_env_file=None)
    chat_provider = build_chat_provider(settings)
    embedding_provider = build_embedding_provider(settings)

    assert isinstance(chat_provider, OllamaChatProvider)
    assert isinstance(embedding_provider, OllamaEmbeddingProvider)
    assert chat_provider.model == "qwen3.5:4b"
    assert embedding_provider.model == "qwen3-embedding:0.6b"
    assert chat_provider.disable_thinking is True
    assert chat_provider.trust_env is False
    assert embedding_provider.trust_env is False


def test_build_factories_can_use_openai_compatible_settings() -> None:
    """Verify separate factories can build OpenAI-compatible providers."""
    settings = Settings(
        _env_file=None,
        llm_provider="openai",
        openai_base_url="http://localhost:11434/v1",
        openai_api_key="ollama",
        openai_model="qwen3.5:4b",
        openai_embedding_model="qwen3-embedding:0.6b",
        openai_trust_env=False,
    )

    chat_provider = build_chat_provider(settings)
    embedding_provider = build_embedding_provider(settings)

    assert isinstance(chat_provider, OpenAICompatibleChatProvider)
    assert isinstance(embedding_provider, OpenAICompatibleEmbeddingProvider)
    assert chat_provider.model == "qwen3.5:4b"
    assert embedding_provider.model == "qwen3-embedding:0.6b"
    assert chat_provider.trust_env is False
    assert embedding_provider.trust_env is False
