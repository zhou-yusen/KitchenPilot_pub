from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    app_name: str = "KitchenPilot"
    app_env: str = "local"
    api_prefix: str = "/api"

    llm_provider: Literal["ollama", "openai"] = "ollama"
    ollama_model: str = "qwen2.5:7b"
    ollama_base_url: str = "http://localhost:11434"
    openai_model: str = "gpt-4o-mini"
    openai_api_key: str = ""

    sqlite_database_url: str = "sqlite:///./kitchenpilot.db"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "recipe_chunks"

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()

