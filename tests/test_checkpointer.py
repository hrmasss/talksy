"""Tests for the LangGraph async checkpointer (SQLite and PostgreSQL paths).

These tests verify:
  1. SQLite checkpointer initialises and can put/get a checkpoint.
  2. PostgreSQL checkpointer initialises when ``AI_DB_URI`` is configured
     (skipped when no live Postgres is available).
  3. ``check_db_connection()`` health check works for both backends.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# 1. SQLite async checkpointer
# ---------------------------------------------------------------------------

class TestSqliteCheckpointer:
    """AsyncSqliteSaver-based checkpointer (no external DB needed)."""

    @pytest.mark.asyncio
    async def test_sqlite_saver_initialises(self, tmp_path: Path):
        """Create an AsyncSqliteSaver against a temp file and verify it works."""
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        db_file = tmp_path / "test_ckpt.sqlite"
        conn = await aiosqlite.connect(str(db_file))
        try:
            saver = AsyncSqliteSaver(conn)
            await saver.setup()
            assert saver is not None
        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_sqlite_put_and_get(self, tmp_path: Path):
        """Round-trip: put a checkpoint into SQLite, then get it back."""
        import aiosqlite
        from langgraph.checkpoint.base import (
            CheckpointMetadata,
            empty_checkpoint,
        )
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        db_file = tmp_path / "test_ckpt_rw.sqlite"
        conn = await aiosqlite.connect(str(db_file))
        try:
            saver = AsyncSqliteSaver(conn)
            await saver.setup()

            thread_id = f"test_{uuid.uuid4().hex[:8]}"
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": "",
                },
            }

            checkpoint = empty_checkpoint()
            metadata = CheckpointMetadata()

            saved_config = await saver.aput(config, checkpoint, metadata, {})
            assert saved_config is not None

            # Retrieve the checkpoint
            got = await saver.aget_tuple(config)
            assert got is not None
            assert got.checkpoint is not None
        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_get_checkpointer_falls_back_to_sqlite(self, tmp_path: Path):
        """When AI_DB_URI is empty, ``get_checkpointer`` should use SQLite."""
        import app.agents.common.checkpointer as ckpt_mod

        # Reset module-level singletons
        ckpt_mod._checkpointer = None
        ckpt_mod._sqlite_saver_instance = None

        with patch.object(ckpt_mod, "settings") as mock_settings:
            mock_settings.ai_db_uri = ""

            # Patch Path so the SQLite file goes into tmp_path
            sqlite_path = tmp_path / "langgraph_checkpoint.sqlite"
            with patch(
                "app.agents.common.checkpointer.Path",
                return_value=sqlite_path,
            ):
                checkpointer = await ckpt_mod.get_checkpointer()
                assert checkpointer is not None

        # Clean up singletons
        ckpt_mod._checkpointer = None
        ckpt_mod._sqlite_saver_instance = None


# ---------------------------------------------------------------------------
# 2. PostgreSQL async checkpointer (integration - skipped without live DB)
# ---------------------------------------------------------------------------

_PG_URI = os.environ.get("AI_DB_URI", "")
_skip_no_pg = pytest.mark.skipif(
    not _PG_URI,
    reason="AI_DB_URI not set - skipping PostgreSQL checkpointer tests",
)


class TestPostgresCheckpointer:
    """AsyncPostgresSaver tests - require a running PostgreSQL instance."""

    @_skip_no_pg
    @pytest.mark.asyncio
    async def test_postgres_saver_initialises(self):
        """Verify AsyncPostgresSaver can connect and set up its tables."""
        from psycopg_pool import AsyncConnectionPool

        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        pool = AsyncConnectionPool(
            conninfo=_PG_URI,
            max_size=2,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        await pool.open()
        try:
            saver = AsyncPostgresSaver(pool)
            await saver.setup()
            assert saver is not None
        finally:
            await pool.close()

    @_skip_no_pg
    @pytest.mark.asyncio
    async def test_postgres_put_and_get(self):
        """Round-trip checkpoint write/read on PostgreSQL."""
        from psycopg_pool import AsyncConnectionPool

        from langgraph.checkpoint.base import (
            CheckpointMetadata,
            empty_checkpoint,
        )
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        pool = AsyncConnectionPool(
            conninfo=_PG_URI,
            max_size=2,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        await pool.open()
        try:
            saver = AsyncPostgresSaver(pool)
            await saver.setup()

            thread_id = f"test_{uuid.uuid4().hex[:8]}"
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": "",
                },
            }

            checkpoint = empty_checkpoint()
            metadata = CheckpointMetadata()

            saved = await saver.aput(config, checkpoint, metadata, {})
            assert saved is not None

            got = await saver.aget_tuple(config)
            assert got is not None
            assert got.checkpoint is not None
        finally:
            await pool.close()


# ---------------------------------------------------------------------------
# 3. Health-check helper
# ---------------------------------------------------------------------------

class TestCheckDbConnection:
    @pytest.mark.asyncio
    async def test_sqlite_health_returns_true(self):
        """Without AI_DB_URI, health check should return True (SQLite)."""
        import app.agents.common.checkpointer as ckpt_mod

        with patch.object(ckpt_mod, "settings") as mock_settings:
            mock_settings.ai_db_uri = ""
            result = await ckpt_mod.check_db_connection()
            assert result is True

    @_skip_no_pg
    @pytest.mark.asyncio
    async def test_postgres_health_returns_true(self):
        """With a live AI_DB_URI, health check should succeed."""
        import app.agents.common.checkpointer as ckpt_mod

        # Reset pool so it reconnects with the real URI
        ckpt_mod._pool = None
        ckpt_mod._checkpointer = None
        ckpt_mod._sqlite_saver_instance = None

        result = await ckpt_mod.check_db_connection()
        assert result is True

        # Cleanup
        await ckpt_mod.close_pool()
        ckpt_mod._pool = None
