from fastapi import APIRouter, HTTPException

from app.graphs.analysis_graph import run_analysis_graph
from app.schemas.analysis import AnalysisQueryRequest, AnalysisQueryResponse
from app.services.errors import RagServiceError


router = APIRouter(
    prefix="/api/analysis",
    tags=["Analysis"],
)


@router.post("/query", response_model=AnalysisQueryResponse)
async def query_analysis(request: AnalysisQueryRequest) -> AnalysisQueryResponse:
    try:
        final_state = await run_analysis_graph(
            question=request.message,
            top_k=request.top_k,
        )

        return AnalysisQueryResponse(
            intent=final_state.get("intent", "UNSUPPORTED"),
            answer=final_state.get("answer", ""),
            sources=final_state.get("sources", []),
            used_context=final_state.get("used_context", False),
            evidence=final_state.get("evidence", []),
            aggregations=final_state.get("aggregations", []),
            dashboard=final_state.get("dashboard"),
        )
    except RagServiceError as e:
        raise HTTPException(status_code=502, detail=e.message)