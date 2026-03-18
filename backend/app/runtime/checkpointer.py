"""LangGraph checkpointer backed by PostgreSQL.

Uses AsyncPostgresSaver for conversation state persistence across runs.
The checkpointer must be set up (create tables) before first use.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings


def _get_conn_string() -> str:
    """Convert asyncpg URL to psycopg-compatible URL for checkpointer."""
    return settings.DATABASE_URL.replace("+asyncpg", "")


@asynccontextmanager
async def get_checkpointer() -> AsyncGenerator[AsyncPostgresSaver, None]:
    async with AsyncPostgresSaver.from_conn_string(_get_conn_string()) as checkpointer:
        await checkpointer.setup()
        yield checkpointer
