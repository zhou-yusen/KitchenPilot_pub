from typing import Protocol

from kitchenpilot.core.config import Settings, get_settings
from kitchenpilot.core.http import auth_headers, post_json


class EmbeddingProvider(Protocol):
    """Define the embedding operation required by retrieval and routing."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate one embedding vector for each input text."""
        ...


class MockEmbeddingProvider:
    """Provide deterministic embeddings for local unit tests."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return tiny deterministic vectors for local unit tests."""
        return [[float(len(text)), float(sum(ord(char) for char in text) % 997)] for text in texts]


class OllamaEmbeddingProvider:
    """Call local Ollama /api/embed without reading proxy settings."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout: float,
        trust_env: bool = False,
    ) -> None:
        """Initialize this embedding provider with its model and HTTP behavior."""
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.trust_env = trust_env

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Call Ollama /api/embed and return one vector per input text."""
        if not texts:
            return []

        data = post_json(
            f"{self.base_url}/api/embed",
            {
                "model": self.model,
                "input": texts,
            },
            timeout=self.timeout,
            trust_env=self.trust_env,
        )
        embeddings = data.get("embeddings", [])
        return [[float(value) for value in vector] for vector in embeddings]


class OpenAICompatibleEmbeddingProvider:
    """Call /embeddings endpoints that follow the OpenAI HTTP API shape."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float,
        trust_env: bool = True,
    ) -> None:
        """Initialize this embedding provider with OpenAI-compatible settings."""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.trust_env = trust_env

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Call /embeddings and return one vector per input text."""
        if not texts:
            return []

        data = post_json(
            f"{self.base_url}/embeddings",
            {
                "model": self.model,
                "input": texts,
            },
            headers=auth_headers(self.api_key),
            timeout=self.timeout,
            trust_env=self.trust_env,
        )
        items = data.get("data", [])
        if not isinstance(items, list):
            return []
        return [
            [float(value) for value in item.get("embedding", [])]
            for item in items
            if isinstance(item, dict)
        ]


def build_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    """Build the configured embedding provider."""
    settings = settings or get_settings()
    if settings.llm_provider == "mock":
        return MockEmbeddingProvider()
    if settings.llm_provider == "ollama":
        return OllamaEmbeddingProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model,
            timeout=settings.llm_timeout,
            trust_env=settings.ollama_trust_env,
        )
    if settings.llm_provider == "openai":
        return OpenAICompatibleEmbeddingProvider(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            timeout=settings.llm_timeout,
            trust_env=settings.openai_trust_env,
        )
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
