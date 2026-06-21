from fastapi import FastAPI

from contextlib import asynccontextmanager

from app.api.routes.rag import router as rag_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.enterprise_agent import router as enterprise_agent_router
from app.api.routes.enterprise_agent_stream import router as enterprise_agent_stream_router
from app.api.routes.chat import router as chat_router
from app.agents.enterprise_agent_graph import (
    initialize_enterprise_agent_graph,
)
from app.memory.checkpoint import (
    close_checkpoint_store,
    open_checkpoint_store,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    checkpointer = await open_checkpoint_store()

    app.state.checkpointer = checkpointer
    app.state.enterprise_agent_graph = (
        initialize_enterprise_agent_graph(checkpointer)
    )

    try:
        yield
    finally:
        await close_checkpoint_store()

app = FastAPI(
    title="Enterprise Search Query Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(rag_router)
app.include_router(analysis_router)
app.include_router(enterprise_agent_router)
app.include_router(enterprise_agent_stream_router)
app.include_router(chat_router)

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
