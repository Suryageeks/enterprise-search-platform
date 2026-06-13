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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
