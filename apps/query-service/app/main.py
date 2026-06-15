from fastapi import FastAPI

from app.api.routes.rag import router as rag_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.enterprise_agent import router as enterprise_agent_router

app = FastAPI(
    title="Enterprise Search Query Service",
    version="0.1.0",
)

app.include_router(rag_router)
app.include_router(analysis_router)
app.include_router(enterprise_agent_router)

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}