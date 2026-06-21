from uuid import uuid4

from fastapi import APIRouter

from app.agents.enterprise_agent_graph import run_enterprise_agent
from app.schemas.enterprise import EnterpriseAgentRequest, EnterpriseAgentResponse

router = APIRouter(
    prefix="/api/agents",
    tags=["Enterprise Agent"],
)

@router.post("/query", response_model=EnterpriseAgentResponse)
async def query_enterprise_agent(request: EnterpriseAgentRequest) -> EnterpriseAgentResponse:
    result = await run_enterprise_agent(
        question=request.question,
        thread_id=f"legacy-{uuid4()}",
    )

    return EnterpriseAgentResponse.model_validate(result)
