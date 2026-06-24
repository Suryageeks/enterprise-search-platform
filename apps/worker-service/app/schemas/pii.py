from pydantic import BaseModel, Field

class PiiDetection(BaseModel):
    entity_type: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    score: float = Field(ge=0, le=1)