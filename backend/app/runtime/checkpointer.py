"""LangGraph checkpointer backed by PostgreSQL.

Uses AsyncPostgresSaver for conversation state persistence across runs.
The checkpointer must be set up (create tables) before first use.

Provides two modes:
    - Per-request context manager: `get_checkpointer()` — for backward compat
    - Persistent lifecycle: `init_checkpointer()` / `close_checkpointer()` — for CopilotKit
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings


def _get_conn_string() -> str:
    """Convert asyncpg URL to psycopg-compatible URL for checkpointer."""
    return settings.DATABASE_URL.replace("+asyncpg", "")


# --------------- Per-request context manager (backward compat) ---------------


@asynccontextmanager
async def get_checkpointer() -> AsyncGenerator[AsyncPostgresSaver, None]:
    async with AsyncPostgresSaver.from_conn_string(_get_conn_string()) as checkpointer:
        await checkpointer.setup()
        yield checkpointer


# --------------- Persistent lifecycle (for CopilotKit pre-compiled graphs) ---------------

_persistent_checkpointer: AsyncPostgresSaver | None = None
_persistent_context: object | None = None  # context manager instance


async def init_checkpointer() -> None:
    """Start a long-lived checkpointer — call once at app startup."""
    global _persistent_checkpointer, _persistent_context

    cm = AsyncPostgresSaver.from_conn_string(_get_conn_string())
    _persistent_context = cm
    _persistent_checkpointer = await cm.__aenter__()
    await _persistent_checkpointer.setup()


async def close_checkpointer() -> None:
    """Shut down the persistent checkpointer — call at app shutdown."""
    global _persistent_checkpointer, _persistent_context

    if _persistent_context is not None:
        await _persistent_context.__aexit__(None, None, None)
    _persistent_checkpointer = None
    _persistent_context = None


def get_persistent_checkpointer() -> AsyncPostgresSaver:
    """Return the long-lived checkpointer instance.

    Raises RuntimeError if `init_checkpointer()` hasn't been called.
    """
    if _persistent_checkpointer is None:
        raise RuntimeError("Persistent checkpointer not initialized — call init_checkpointer()")
    return _persistent_checkpointer
