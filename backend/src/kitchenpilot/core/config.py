from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE = PROJECT_ROOT / ".env"
LLMProviderName = Literal["ollama", "openai", "mimo", "mock"]
EmbeddingProviderName = Literal["ollama", "openai", "mock"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    app_name: str = "KitchenPilot"
    app_env: str = "local"
    api_prefix: str = "/api"

    llm_provider: LLMProviderName = "ollama"
    embedding_provider: EmbeddingProviderName | None = Field(
        default=None,
        validation_alias=AliasChoices("EMBEDDING_PROVIDER", "EMBED_MODEL_TYPE"),
    )
    llm_timeout: float = 60.0
    ollama_model: str = "qwen3.5:4b"
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = Field(
        default="qwen3-embedding:0.6b",
        validation_alias=AliasChoices("OLLAMA_EMBEDDING_MODEL", "EMBED_MODEL_NAME"),
    )
    ollama_disable_thinking: bool = True
    ollama_trust_env: bool = False
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_disable_thinking: bool = True
    openai_trust_env: bool = True
    mimo_model: str = "mimo-v2.5"
    mimo_base_url: str = "https://api.xiaomimimo.com/v1"
    mimo_api_key: str = ""
    mimo_disable_thinking: bool = True
    mimo_trust_env: bool = True

    sqlite_database_url: str = "sqlite:///./kitchenpilot.db"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "recipe_chunks"
    qdrant_vector_size: int = 1024
    qdrant_timeout: float = 5.0
    rag_use_qdrant: bool = True

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def resolved_embedding_provider(self) -> EmbeddingProviderName:
        """Return the explicit embedding provider or the chat-compatible default."""
        if self.embedding_provider:
            return self.embedding_provider
        if self.llm_provider == "openai":
            return "openai"
        if self.llm_provider == "mock":
            return "mock"
        return "ollama"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
