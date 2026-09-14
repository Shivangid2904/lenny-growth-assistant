from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "info"

    # Database
    database_url: str = "postgresql://postgres:postgrespassword@localhost:5432/lenny_growth"
    test_database_url: str = "postgresql://postgres:postgrespassword@localhost:5432/lenny_growth_test"

    # LLM Providers ("anthropic" or "ollama")
    llm_provider: str = "ollama"  # Docker demo default; local dev can override via .env
    default_llm_provider: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # Local Ollama
    ollama_base_url: str = "http://localhost:11434"  # Local dev default; Docker overrides via compose
    ollama_model: str = "llama3.2:latest"
    ollama_embedding_model: str = "nomic-embed-text"
    embedding_model: str = "nomic-embed-text"
    embedding_dimension: int = 768

    # RAG & Agent Settings
    # NOTE: 0.35 is a development placeholder value. Must be recalibrated after real Lenny transcript corpus ingestion.
    rag_relevance_distance_threshold: float = 0.35
    # NOTE: 10 messages (approx. 5 turns) MVP history window. Configurable for future tuning.
    conversation_history_limit: int = 10
    # NOTE: 60 seconds model timeout MVP default.
    model_timeout_seconds: float = 60.0

    # Ports
    backend_port: int = 8000
    frontend_port: int = 5173

    # CORS — set CORS_ALLOWED_ORIGINS as a JSON array string in production,
    # e.g. CORS_ALLOWED_ORIGINS='["https://your-frontend-domain.com"]'
    # Development defaults cover standard Vite dev-server ports.
    cors_allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @property
    def active_llm_provider(self) -> str:
        # Map "local"/"cloud" to actual provider names for user convenience
        prov = (self.llm_provider or self.default_llm_provider or "anthropic").lower().strip()

        # Map user-friendly names to internal provider names
        if prov in ("local", "ollama"):
            return "ollama"
        if prov in ("cloud", "claude", "anthropic"):
            return "anthropic"
        return prov

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

