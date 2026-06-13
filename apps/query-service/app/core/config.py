from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    google_api_key: str = Field(
        validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    )

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "documents"

    chat_model: str = "gemini-3.5-flash"
    max_output_tokens: int = 1024


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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
