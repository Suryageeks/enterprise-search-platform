from fastapi import FastAPI

from app.api.routes.rag import router as rag_router

app = FastAPI(
    title="query-service",
    version="0.1.0",
)

app.include_router(rag_router)

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}