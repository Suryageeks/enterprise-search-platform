from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "worker-service"
    env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8090

    redis_url: str 
    redis_stream_name: str
    redis_consumer_group: str 
    redis_consumer_name: str

    aws_region: str
    aws_endpoint_url: str 
    aws_access_key_id: str 
    aws_secret_access_key: str 
    aws_bucket_name: str 

    postgres_dsn: str
    qdrant_url: str
    qdrant_collection_name: str
    qdrant_collection_alias: str = "documents"
    qdrant_vector_distance: str = "cosine"

    opensearch_url: str = "http://localhost:9200"
    opensearch_log_index: str = "normalized-logs"
    opensearch_username: str | None = None
    opensearch_password: str | None = None
    opensearch_use_ssl: bool = False
    opensearch_verify_certs: bool = False

    embedding_model: str = "bert-base-uncased"
    embedding_batch_size: int = 32
    embedding_device: str = "cpu"

    pii_masking_enabled: bool = True
    pii_model_name: str = (
        "Isotonic/distilbert_finetuned_ai4privacy_v2"
    )

    pii_score_threshold: float = 0.60
    pii_max_tokens: int = 384
    pii_stride: int = 32
    pii_device: str = "cpu"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # type: ignore[call-arg]
