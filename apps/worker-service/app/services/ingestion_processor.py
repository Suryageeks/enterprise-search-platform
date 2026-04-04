from app.clients.postgres_client import postgres_status_client
from app.schemas.ingestion import IngestionJobMessage
import logging

logger = logging.getLogger(__name__)


class IngestionProcessor:
    async def process(self, message: IngestionJobMessage) -> None:
        await postgres_status_client.mark_processing(message.jobId, message.docId)
        try:
            # Placeholder orchestration for:
            # 1. download from S3
            # 2. parse/chunk
            # 3. embed
            # 4. upsert to Qdrant
            # 5. update Postgres status
            await postgres_status_client.mark_completed(message.jobId, message.docId)
        except Exception as exc:
            logger.exception("Error marking job as completed")
            await postgres_status_client.mark_failed(message.jobId, message.docId, str(exc))
            raise


ingestion_processor = IngestionProcessor()
