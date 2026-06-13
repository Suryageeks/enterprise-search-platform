from fastapi import APIRouter

from app.graphs.analysis_graph import run_analysis_graph
from app.schemas.analysis import AnalysisQueryRequest, AnalysisQueryResponse


router = APIRouter(
    prefix="/api/analysis",
    tags=["Analysis"],
)


@router.post("/query", response_model=AnalysisQueryResponse)
async def query_analysis(request: AnalysisQueryRequest) -> AnalysisQueryResponse:
    final_state = await run_analysis_graph(
        question=request.message,
        top_k=request.top_k,
    )

    return AnalysisQueryResponse(
        intent=final_state.get("intent", "UNSUPPORTED"),
        answer=final_state.get("answer", ""),
        sources=final_state.get("sources", []),
    )