from datetime import datetime

from pydantic import BaseModel


class IngestionJobMessage(BaseModel):
    jobId: str
    docId: str
    empId: str
    fileName: str
    filePath: str
    uploadType: str
    queuedAt: datetime
