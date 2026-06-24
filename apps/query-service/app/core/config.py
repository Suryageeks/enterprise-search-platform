from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    google_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    )

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "documents"

    chat_model: str = "gemini-3.5-flash"
    temperature: float = 0.2
    max_output_tokens: int = 700

    enable_ollama_fallback: bool = True
    ollama_model: str = "qwen3.5:2b"
    ollama_host: str = "http://localhost:11434"


    embedding_model: str = "bert-base-uncased"
    embedding_device: str = "cpu"

    default_top_k: int = 5
    max_context_chars: int = 8000

    opensearch_url: str = "http://localhost:9200"
    opensearch_index: str = "normalized-logs"
    opensearch_username: str | None = None
    opensearch_password: str | None = None
    opensearch_use_ssl: bool = False
    opensearch_verify_certs: bool = False
    app_timezone: str = "Asia/Kolkata"

    database_url: str = "postgresql+asyncpg://admin:admin@localhost:5433/aisearchdb"
    langgraph_checkpoint_url: str = (
        "postgresql://admin:admin@localhost:5433/aisearchdb"
    )

    agent_read_database_url: str = (
        "postgresql+asyncpg://agent_reader:"
        "agent_reader_local_password@localhost:5433/aisearchdb"
    )

    mlflow_enabled: bool = True
    mlflow_tracking_uri: str = "http://localhost:5050"
    mlflow_experiment_name: str = "enterprise-log-agent"

    dashboard_use_gemini: bool = True

    max_log_search_size: int = 100
    max_aggregation_size: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
