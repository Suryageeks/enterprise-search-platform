from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.config import settings

checkpoint_pool = AsyncConnectionPool(
    conninfo=settings.langgraph_checkpoint_url,
    min_size=1,
    max_size=10,
    open=False,
    kwargs={
        "autocommit": True,
        "prepare_threshold": 0,
        "row_factory": dict_row,
    },
)

async def open_checkpoint_store() -> AsyncPostgresSaver:
    await checkpoint_pool.open()
    await checkpoint_pool.wait()

    checkpointer = AsyncPostgresSaver(checkpoint_pool)

    await checkpointer.setup()

    return checkpointer

async def close_checkpoint_store() -> None:
    await checkpoint_pool.close()

