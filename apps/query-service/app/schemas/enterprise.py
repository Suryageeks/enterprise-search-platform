from pydantic import BaseModel, Field

class EnterpriseAgentRequest(BaseModel):
    question: str = Field(..., min_length=1)


class EnterpriseAgentResponse(BaseModel):
    answer: str