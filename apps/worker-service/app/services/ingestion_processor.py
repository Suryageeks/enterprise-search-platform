from math import log

from app.clients.s3_client import s3_client
from app.clients.postgres_client import postgres_status_client
from app.schemas.ingestion import IngestionJobMessage
import logging

from app.services.text_chunker import text_chunker
from app.services.file_parser import file_parser

logger = logging.getLogger(__name__)


class IngestionProcessor:
    async def process(self, message: IngestionJobMessage) -> None:
        await postgres_status_client.mark_processing(message.jobId, message.docId)
        try:
            # Placeholder orchestration for:
            # 1. download from S3
            file_bytes = await s3_client.download_bytes(message.filePath)
            
            # 2. extract text
            extract_text = await file_parser.extract_text(
                message.fileName,
                file_bytes
            )
            
            # 3. chunk
            chunks = text_chunker.chunk_text(extract_text)
            
            logger.info(
                "Downloaded file for job=%s doc=%s key=%s chunks=%s",
                message.jobId,
                message.docId,
                message.filePath,
                len(chunks),
            )            
            
            # 4. embed
            # 5. upsert to Qdrant
            
            # 6. update Postgres status
            await postgres_status_client.mark_completed(message.jobId, message.docId)
        except Exception as exc:
            logger.exception("Error marking job as completed")
            await postgres_status_client.mark_failed(message.jobId, message.docId, str(exc))
            raise


ingestion_processor = IngestionProcessor()
