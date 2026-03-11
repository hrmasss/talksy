"""Async Checkpointer for LangGraph.

Uses ``psycopg`` + ``AsyncConnectionPool`` for PostgreSQL.
Falls back to ``AsyncSqliteSaver`` (aiosqlite) when no ``AI_DB_URI`` is configured.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import settings
from app.core.logging import logger

# Import the SQLite saver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

if TYPE_CHECKING:
    from psycopg_pool import AsyncConnectionPool

# ---------------------------------------------------------------------------
# Connection pool (module-level singleton for PostgreSQL)
# ---------------------------------------------------------------------------

_pool: AsyncConnectionPool | None = None


async def _get_pool() -> AsyncConnectionPool:
    """Lazily create and return the async connection pool."""
    global _pool
    if _pool is None:
        from psycopg_pool import AsyncConnectionPool

        if not settings.ai_db_uri:
            raise RuntimeError("AI_DB_URI is not configured, cannot create PostgreSQL pool.")

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
    """Return ``True`` when the configured database is reachable."""
    max_retries = 3
    delay = 1.0

    # If using SQLite fallback, we assume it's always "reachable" locally 
    # unless there are permission issues, which usually raise immediately.
    if not settings.ai_db_uri:
        return True

    for attempt in range(max_retries):
        try:
            pool = await _get_pool()
            async with pool.connection() as conn, conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()
            return True
        except Exception as exc:
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.error("AI DB connection failed after {} attempts: {}", max_retries, exc)
    return False


# ---------------------------------------------------------------------------
# Async checkpointer (singleton)
# ---------------------------------------------------------------------------

_checkpointer = None
_sqlite_saver_instance = None


async def get_checkpointer():
    """Return (and lazily create) the async checkpointer.

    * **PostgreSQL** when ``AI_DB_URI`` is set.
    * **AsyncSqliteSaver** otherwise (persistent local storage).
    """
    global _checkpointer, _sqlite_saver_instance
    
    if _checkpointer is not None:
        return _checkpointer

    if settings.ai_db_uri:
        # --- PostgreSQL Path ---
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            pool = await _get_pool()
            _checkpointer = AsyncPostgresSaver(pool)
            await _checkpointer.setup()
            logger.info("AsyncPostgresSaver checkpointer initialised")
            return _checkpointer
        except ImportError:
            logger.error("langgraph-checkpoint-postgres not installed")
            raise RuntimeError("PostgreSQL saver requested but library missing.") from None
        except Exception as exc:
            logger.opt(exception=exc).error("PostgreSQL checkpointer failed")
            raise RuntimeError(f"Failed to initialize PostgreSQL saver: {exc}") from exc

    else:
        # --- SQLite Fallback Path ---
        try:
            # Define a local file for persistence
            db_path = Path("./langgraph_checkpoint.sqlite")

            # AsyncSqliteSaver.from_conn_string returns an async context
            # manager, but we need a long-lived instance.  Use the private
            # constructor via aiosqlite directly instead.
            import aiosqlite

            conn = await aiosqlite.connect(str(db_path))
            _sqlite_saver_instance = AsyncSqliteSaver(conn)
            await _sqlite_saver_instance.setup()

            _checkpointer = _sqlite_saver_instance
            logger.info("AsyncSqliteSaver checkpointer initialised at {}", db_path.resolve())
            return _checkpointer
        except Exception as exc:
            logger.opt(exception=exc).error("Failed to initialize SQLite saver")
            raise RuntimeError(f"Failed to initialize fallback SQLite saver: {exc}") from exc


# ---------------------------------------------------------------------------
# Thread management
# ---------------------------------------------------------------------------

async def delete_thread(thread_id: str) -> None:
    """Remove all checkpoint data for *thread_id*."""
    
    # If using SQLite, the instance handles deletion via its API usually, 
    # but since we don't have direct SQL access to the SQLite instance easily 
    # without exposing internals, we rely on the checkpointer's put/get logic 
    # or execute raw SQL if we can get a connection.
    # However, LangGraph savers often don't expose a raw "delete thread" method 
    # publicly in the base class. 
    
    # For PostgreSQL:
    if settings.ai_db_uri:
        try:
            pool = await _get_pool()
            async with pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM checkpoints WHERE thread_id = %s",
                    (thread_id,),
                )
                await cur.execute(
                    "DELETE FROM checkpoint_writes WHERE thread_id = %s",
                    (thread_id,),
                )
        except Exception as e:
            logger.opt(exception=e).error("Error deleting thread {} from Postgres", thread_id)
            
    # For SQLite:
    # The AsyncSqliteSaver stores data in tables similar to Postgres.
    # We can attempt to access the underlying connection if needed, 
    # but strictly speaking, without exposing the internal conn of AsyncSqliteSaver,
    # we might need to rely on the library providing a cleanup method in future versions.
    # Below is an attempt to run raw SQL on the SQLite file directly if necessary,
    # though typically one might just let the data sit or implement a specific cleanup routine.
    else:
        if _sqlite_saver_instance:
            # Note: Accessing internal _conn of AsyncSqliteSaver is fragile and depends on library version.
            # A safer approach for SQLite deletion without raw SQL access is often not available 
            # in the public API of older LangGraph versions. 
            # If you need strict deletion for SQLite, you may need to open a separate aiosqlite connection.
            import aiosqlite
            db_path = Path("./langgraph_checkpoint.sqlite")
            try:
                async with aiosqlite.connect(str(db_path)) as conn:
                    await conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
                    await conn.execute("DELETE FROM checkpoint_writes WHERE thread_id = ?", (thread_id,))
                    await conn.commit()
            except Exception as e:
                logger.opt(exception=e).error("Error deleting thread {} from SQLite", thread_id)