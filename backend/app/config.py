from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "info"

    # Database
    database_url: str = "postgresql://postgres:postgrespassword@localhost:5432/lenny_growth"
    test_database_url: str = "postgresql://postgres:postgrespassword@localhost:5432/lenny_growth_test"

    # LLM Providers
    default_llm_provider: str = "claude"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # Local Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3:latest"
    embedding_model: str = "nomic-embed-text"

    # Ports
    backend_port: int = 8000
    frontend_port: int = 3000

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
