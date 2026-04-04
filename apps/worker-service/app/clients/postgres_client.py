from sqlalchemy import text, update

from app.db.database import AsyncSessionLocal
from app.db.models import Document, IngestionJob


class PostgresStatusClient:
    async def ping(self) -> bool:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    
    async def mark_processing(self, job_id: str, doc_id: str) -> None:
        _ = (job_id, doc_id)
        await self.update_doc_status(job_id, doc_id, status="PROCESSING", clear_error=True)

    async def mark_completed(self, job_id: str, doc_id: str) -> None:
        _ = (job_id, doc_id)
        await self.update_doc_status(job_id, doc_id, status="COMPLETED", clear_error=True)

    async def mark_failed(self, job_id: str, doc_id: str, error_message: str) -> None:
        _ = (job_id, doc_id, error_message)
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(IngestionJob)
                .where(IngestionJob.job_id == job_id)
                .values(
                    status="FAILED",
                    error_message=error_message[:2000],
                    updated_at=text("CURRENT_TIMESTAMP"),
                )
            )
            
            await session.execute(
                update(Document)
                .where(Document.doc_id == doc_id)
                .values(
                    file_status="FAILED",
                    updated_at=text("CURRENT_TIMESTAMP"),
                )
            )
            
            await session.commit()
    
    async def update_doc_status(self, job_id: str, doc_id: str, status: str, clear_error: bool = False) -> None:
        async with AsyncSessionLocal() as session:
            ingestion_values = {
                "status": status,
                "updated_at": text("CURRENT_TIMESTAMP"),
            }
            
            document_values = {
                "file_status": status,
                "updated_at": text("CURRENT_TIMESTAMP"),
            }
            
            if clear_error:
                ingestion_values["error_message"] = None
                
            await session.execute(
                update(IngestionJob)
                .where(IngestionJob.job_id == job_id)
                .values(**ingestion_values)
            )
            
            await session.execute(
                update(Document)
                .where(Document.doc_id == doc_id)
                .values(**document_values)
            )
            
            await session.commit()


postgres_status_client = PostgresStatusClient()
