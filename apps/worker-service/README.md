# Worker Service

FastAPI worker service for asynchronous ingestion processing.

Responsibilities:
- consume ingestion jobs from Redis Streams
- download raw files from S3-compatible storage
- parse and chunk document content
- generate embeddings
- upsert vectors into Qdrant
- update ingestion status in Postgres

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8090
```

## Initial Layout

- `app/main.py`: FastAPI entrypoint
- `app/core/config.py`: environment configuration
- `app/api/routes/health.py`: service health endpoints
- `app/consumers/redis_consumer.py`: Redis stream consumer placeholder
- `app/services/ingestion_processor.py`: ingestion orchestration
- `app/clients/`: S3, Qdrant, embeddings, and Postgres client placeholders
- `app/schemas/ingestion.py`: ingestion payload schemas
