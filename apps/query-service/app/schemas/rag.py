from pydantic import BaseModel, Field

class RagQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The user's query to be processed.")
    top_k: int = Field(default=5, ge=1, le=20, description="The number of top relevant documents to retrieve from the vector database.")

class RagSource(BaseModel):
    doc_id: str | None = None
    file_name: str | None = None
    chunk_index: int | None = None
    score: float | None = None
    text_preview: str

class RagQueryResponse(BaseModel):
    answer: str
    sources: list[RagSource]