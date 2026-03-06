"""Async PostgreSQL checkpointer for LangGraph.

Uses ``psycopg`` + ``AsyncConnectionPool`` so all graph executions
share a single connection pool.  Falls back to ``MemorySaver`` when no
``AI_DB_URI`` is configured.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from langgraph.checkpoint.memory import MemorySaver

from app.config import settings

if TYPE_CHECKING:
    from psycopg_pool import AsyncConnectionPool

# ---------------------------------------------------------------------------
# Connection pool (module-level singleton)
# ---------------------------------------------------------------------------

_pool: AsyncConnectionPool | None = None


async def _get_pool() -> AsyncConnectionPool:
    """Lazily create and return the async connection pool."""
    global _pool
    if _pool is None:
        from psycopg_pool import AsyncConnectionPool

        _pool = AsyncConnectionPool(
            conninfo=settings.ai_db_uri,
            max_size=20,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
            },
        )
        await _pool.open()
    return _pool


async def close_pool() -> None:
    """Gracefully close the pool – call from ``on_shutdown``."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

async def check_db_connection() -> bool:
    """Return ``True`` when the AI database is reachable."""
    max_retries = 3
    delay = 1.0

    for attempt in range(max_retries):
        try:
            if not settings.ai_db_uri:
                return True  # nothing to check

            pool = await _get_pool()
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    await cur.fetchone()
            return True
        except Exception as exc:  # noqa: BLE001
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                print(f"AI DB connection failed after {max_retries} attempts: {exc}")
    return False


# ---------------------------------------------------------------------------
# Async checkpointer (singleton)
# ---------------------------------------------------------------------------

_checkpointer = None


async def get_checkpointer():
    """Return (and lazily create) the async checkpointer.

    * **PostgreSQL** when ``AI_DB_URI`` is set.
    * **MemorySaver** otherwise (dev convenience – no persistence).
    """
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    if settings.ai_db_uri:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            pool = await _get_pool()
            _checkpointer = AsyncPostgresSaver(pool)
            await _checkpointer.setup()
            print("✅ AsyncPostgresSaver checkpointer initialised")
            return _checkpointer
        except ImportError:
            print("⚠️  langgraph-checkpoint-postgres not installed – using MemorySaver")
        except Exception as exc:
            print(f"⚠️  PostgreSQL checkpointer failed ({exc}) – using MemorySaver")

    _checkpointer = MemorySaver()
    print("⚠️  Using MemorySaver (in-memory only, no persistence)")
    return _checkpointer


# ---------------------------------------------------------------------------
# Thread management
# ---------------------------------------------------------------------------

async def delete_thread(thread_id: str) -> None:
    """Remove all checkpoint data for *thread_id*."""
    if not settings.ai_db_uri:
        return

    try:
        pool = await _get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM checkpoints WHERE thread_id = %s",
                    (thread_id,),
                )
                await cur.execute(
                    "DELETE FROM checkpoint_writes WHERE thread_id = %s",
                    (thread_id,),
                )
    except Exception:  # noqa: BLE001
        pass  # table may not exist yet
