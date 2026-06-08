import pathlib
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "Analytics Copilot"
    version: str = "0.1.0"
    environment: str = "dev"
    log_level: str = "INFO"

    core_api_port: int = 8090

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "analytics_copilot"
    postgres_user: str = "postgres"
    postgres_password: SecretStr = SecretStr("postgres")

    # Read-only role used by the SQL executor
    postgres_ro_user: str = "analyst_ro"
    postgres_ro_password: SecretStr = SecretStr("analyst_ro")

    openai_api_key: SecretStr | None = None

    # Legacy / reference — kept from OpenRAG skeleton
    database_url: str | None = None
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334
    qdrant_api_key: SecretStr | None = None
    qdrant_collection_name: str = "openrag_documents"

    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    model_config = SettingsConfigDict(
        env_file=pathlib.Path(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
