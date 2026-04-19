"""Application configuration settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Talksy"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"
    secret_key: str = Field(default="change-me-in-production-please")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    # Database - PostgreSQL is primary, SQLite for dev convenience
    db_engine: Literal["sqlite", "postgres"] = "postgres"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "talksy"
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_sqlite_path: str = Field(default="")

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AI / LLM - Groq
    groq_api_key: str = ""
    groq_api_keys: str = ""  # comma-separated list of Groq API keys
    groq_model: str = "llama-3.3-70b-versatile"
    groq_tts_model: str = "canopylabs/orpheus-v1-english"
    groq_tts_voice: str = "troy"
    groq_stt_model: str = "whisper-large-v3-turbo"
    groq_tts_sample_rate: int = 24000
    tavily_api_key: str = ""
    serper_api_key: str = ""
    embedding_model: str = "models/text-embedding-004"
    embedding_provider: Literal["google", "huggingface"] = "huggingface"
    huggingface_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Qdrant - long-term memory vector store
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection_prefix: str = "talksy"
    qdrant_embedding_dim: int = 768  # auto-resolved per provider

    # AI Database (for LangGraph checkpointer)
    ai_db_uri: str = ""

    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent.parent.resolve()
    static_dir: Path = Field(default=None)
    templates_dir: Path = Field(default=None)

    @field_validator("static_dir", mode="before")
    @classmethod
    def set_static_dir(cls, v, info):
        if v is None:
            base = info.data.get("base_dir", Path(__file__).parent.parent.parent.parent.resolve())
            return base / "static"
        return Path(v)

    @field_validator("templates_dir", mode="before")
    @classmethod
    def set_templates_dir(cls, v, info):
        if v is None:
            base = info.data.get("base_dir", Path(__file__).parent.parent.parent.parent.resolve())
            return base / "templates"
        return Path(v)

    @field_validator("db_sqlite_path", mode="before")
    @classmethod
    def set_sqlite_path(cls, v, info):
        if not v:
            # Default to project root
            base = Path(__file__).parent.parent.parent.parent.resolve()
            return str(base / "talksy.db")
        return v

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            lowered = v.strip().lower()
            if lowered in {"1", "true", "yes", "on", "debug", "development", "dev"}:
                return True
            if lowered in {"0", "false", "no", "off", "release", "production", "prod"}:
                return False
        return v

    @property
    def database_url(self) -> str:
        """Generate database URL based on engine type."""
        if self.db_engine == "sqlite":
            return f"sqlite:///{self.db_sqlite_path}"
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
