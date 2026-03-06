"""Tests for the Qdrant-backed long-term memory system.

Covers:
  1. Qdrant client connectivity
  2. Store and retrieve (semantic search) round-trip
  3. Category-filtered retrieval
  4. Deletion
  5. Progress summary

All tests use an **in-memory** Qdrant client (via ``QdrantClient(":memory:")``)
and a lightweight **fake embeddings** class so no external server or API key is
needed.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest

from app.memory.client import collection_name_for
from app.memory.models import MemoryCategory, MemoryEntry, MemorySearchResult
from app.memory.service import MemoryService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DIM = 8  # tiny dimension for tests


class _FakeEmbeddings:
    """Deterministic embeddings that hash the input text into a fixed-size vector."""

    def __init__(self, dim: int = _DIM) -> None:
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        h = hash(text) & 0xFFFFFFFF
        return [((h >> i) & 1) * 2.0 - 1.0 for i in range(self.dim)]

    async def aembed_query(self, text: str) -> list[float]:
        return self._vec(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


def _in_memory_client():
    from qdrant_client import QdrantClient
    return QdrantClient(":memory:")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def memory_service():
    """Return a fresh MemoryService wired to an in-memory Qdrant + fake embeddings."""
    svc = MemoryService()
    client = _in_memory_client()
    embeddings = _FakeEmbeddings()

    with (
        patch("app.memory.service.get_qdrant_client", return_value=client),
        patch("app.memory.service.get_embeddings", return_value=embeddings),
        patch("app.memory.service.get_embedding_dim", return_value=_DIM),
    ):
        yield svc


# ---------------------------------------------------------------------------
# 1. Qdrant client connectivity
# ---------------------------------------------------------------------------

class TestQdrantConnection:
    """Verify that the Qdrant client can be created and is reachable."""

    def test_in_memory_client_is_alive(self):
        """An in-memory Qdrant client should respond immediately."""
        client = _in_memory_client()
        collections = client.get_collections()
        assert collections is not None
        assert isinstance(collections.collections, list)

    def test_create_and_list_collection(self):
        """Create a collection and confirm it's listed."""
        from qdrant_client import models as qm

        client = _in_memory_client()
        name = f"test_{uuid.uuid4().hex[:6]}"
        client.create_collection(
            collection_name=name,
            vectors_config=qm.VectorParams(size=_DIM, distance=qm.Distance.COSINE),
        )
        names = [c.name for c in client.get_collections().collections]
        assert name in names


# ---------------------------------------------------------------------------
# 2. Store & retrieve (semantic search round-trip)
# ---------------------------------------------------------------------------

class TestStoreAndRetrieve:
    """Store memories then semantic-search them back."""

    @pytest.mark.asyncio
    async def test_store_single_and_search(self, memory_service: MemoryService):
        user = f"u_{uuid.uuid4().hex[:6]}"
        entry = await memory_service.store(
            user_id=user,
            category=MemoryCategory.WRITING,
            content="User struggles with coherence in essay writing",
            importance=0.8,
        )
        assert isinstance(entry, MemoryEntry)
        assert entry.user_id == user
        assert entry.category == MemoryCategory.WRITING

        results = await memory_service.search(
            user_id=user,
            query="essay coherence problems",
            top_k=3,
        )
        assert len(results) >= 1
        assert isinstance(results[0], MemorySearchResult)
        assert results[0].entry.content == entry.content

    @pytest.mark.asyncio
    async def test_store_many_and_search(self, memory_service: MemoryService):
        user = f"u_{uuid.uuid4().hex[:6]}"
        entries = [
            MemoryEntry(
                user_id=user,
                category=MemoryCategory.SPEAKING,
                content="Good pronunciation but limited vocabulary",
                importance=0.7,
            ),
            MemoryEntry(
                user_id=user,
                category=MemoryCategory.SPEAKING,
                content="Fluent in casual conversation topics",
                importance=0.5,
            ),
        ]
        stored = await memory_service.store_many(entries)
        assert len(stored) == 2

        results = await memory_service.search(
            user_id=user,
            query="vocabulary pronunciation",
            category=MemoryCategory.SPEAKING,
            top_k=5,
        )
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_filters_by_user(self, memory_service: MemoryService):
        """Memories from user A must not appear in user B's search."""
        user_a = f"a_{uuid.uuid4().hex[:6]}"
        user_b = f"b_{uuid.uuid4().hex[:6]}"

        await memory_service.store(
            user_id=user_a,
            category=MemoryCategory.WEAKNESS,
            content="Weak grammar in writing",
        )
        await memory_service.store(
            user_id=user_b,
            category=MemoryCategory.WEAKNESS,
            content="Weak listening comprehension",
        )

        results_a = await memory_service.search(
            user_id=user_a, query="weakness"
        )
        assert all(r.entry.user_id == user_a for r in results_a)


# ---------------------------------------------------------------------------
# 3. Category-filtered retrieval
# ---------------------------------------------------------------------------

class TestCategoryRetrieval:
    @pytest.mark.asyncio
    async def test_get_by_category(self, memory_service: MemoryService):
        user = f"u_{uuid.uuid4().hex[:6]}"
        await memory_service.store(
            user_id=user,
            category=MemoryCategory.STRENGTH,
            content="Excellent reading speed",
        )
        await memory_service.store(
            user_id=user,
            category=MemoryCategory.WEAKNESS,
            content="Poor time management",
        )

        strengths = await memory_service.get_by_category(
            user_id=user, category=MemoryCategory.STRENGTH
        )
        assert len(strengths) == 1
        assert strengths[0].category == MemoryCategory.STRENGTH

    @pytest.mark.asyncio
    async def test_search_with_category_filter(self, memory_service: MemoryService):
        user = f"u_{uuid.uuid4().hex[:6]}"
        await memory_service.store(
            user_id=user,
            category=MemoryCategory.EXAM_RESULT,
            content="Speaking exam band 6.5",
        )
        await memory_service.store(
            user_id=user,
            category=MemoryCategory.GOAL,
            content="Target band 7.5 in speaking",
        )

        results = await memory_service.search(
            user_id=user,
            query="speaking band",
            category=MemoryCategory.EXAM_RESULT,
        )
        assert all(
            r.entry.category == MemoryCategory.EXAM_RESULT for r in results
        )


# ---------------------------------------------------------------------------
# 4. Deletion
# ---------------------------------------------------------------------------

class TestDeletion:
    @pytest.mark.asyncio
    async def test_delete_single(self, memory_service: MemoryService):
        user = f"u_{uuid.uuid4().hex[:6]}"
        entry = await memory_service.store(
            user_id=user,
            category=MemoryCategory.FEEDBACK,
            content="Try using more complex sentences",
        )
        ok = await memory_service.delete(memory_id=entry.id)
        assert ok is True

        results = await memory_service.search(
            user_id=user, query="complex sentences"
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_user_memories_by_category(
        self, memory_service: MemoryService
    ):
        user = f"u_{uuid.uuid4().hex[:6]}"
        await memory_service.store(
            user_id=user,
            category=MemoryCategory.VOCABULARY,
            content="Learned word: ubiquitous",
        )
        await memory_service.store(
            user_id=user,
            category=MemoryCategory.GRAMMAR,
            content="Practiced conditionals",
        )

        deleted = await memory_service.delete_user_memories(
            user_id=user, category=MemoryCategory.VOCABULARY
        )
        assert deleted >= 1

        remaining = await memory_service.get_by_category(
            user_id=user, category=MemoryCategory.VOCABULARY
        )
        assert len(remaining) == 0

        # Grammar should still be there
        grammar = await memory_service.get_by_category(
            user_id=user, category=MemoryCategory.GRAMMAR
        )
        assert len(grammar) == 1


# ---------------------------------------------------------------------------
# 5. Progress summary
# ---------------------------------------------------------------------------

class TestProgressSummary:
    @pytest.mark.asyncio
    async def test_progress_summary(self, memory_service: MemoryService):
        user = f"u_{uuid.uuid4().hex[:6]}"
        await memory_service.store(
            user_id=user,
            category=MemoryCategory.EXAM_RESULT,
            content="Writing exam band 6.0",
            metadata={"section": "writing", "band_score": 6.0},
            importance=0.9,
        )
        await memory_service.store(
            user_id=user,
            category=MemoryCategory.STRENGTH,
            content="Good task achievement",
        )
        await memory_service.store(
            user_id=user,
            category=MemoryCategory.WEAKNESS,
            content="Needs more cohesive devices",
        )
        await memory_service.store(
            user_id=user,
            category=MemoryCategory.GOAL,
            content="Reach band 7.0 by December",
        )

        summary = await memory_service.get_progress_summary(user_id=user)
        assert summary.user_id == user
        assert summary.total_memories == 4
        assert "exam_result" in summary.categories
        assert len(summary.strengths) == 1
        assert len(summary.weaknesses) == 1
        assert len(summary.goals) == 1


# ---------------------------------------------------------------------------
# 6. Convenience helpers
# ---------------------------------------------------------------------------

class TestConvenienceHelpers:
    @pytest.mark.asyncio
    async def test_store_exam_result(self, memory_service: MemoryService):
        user = f"u_{uuid.uuid4().hex[:6]}"
        entries = await memory_service.store_exam_result(
            user_id=user,
            section="speaking",
            band_score=7.0,
            strengths=["Fluent delivery", "Good pronunciation"],
            weaknesses=["Limited vocabulary range"],
            recommendations=["Read more academic texts"],
            report_summary="Overall good speaking performance.",
        )
        # Should create: exam_result + 2 strengths + 1 weakness
        #               + activity log + speaking section entry = 6
        assert len(entries) == 6

    @pytest.mark.asyncio
    async def test_store_user_activity(self, memory_service: MemoryService):
        user = f"u_{uuid.uuid4().hex[:6]}"
        entry = await memory_service.store_user_activity(
            user_id=user,
            action="exam_started",
            detail="Started writing exam",
            metadata={"section": "writing"},
        )
        assert entry.category == MemoryCategory.USER_ACTIVITY
        assert "exam_started" in entry.content

    @pytest.mark.asyncio
    async def test_recall_for_exam(self, memory_service: MemoryService):
        user = f"u_{uuid.uuid4().hex[:6]}"
        await memory_service.store(
            user_id=user,
            category=MemoryCategory.WRITING,
            content="Previously scored band 5.5 on Task 2",
        )
        await memory_service.store(
            user_id=user,
            category=MemoryCategory.WEAKNESS,
            content="Weak coherence in writing",
            metadata={"section": "writing"},
        )

        context = await memory_service.recall_for_exam(
            user_id=user, section="writing"
        )
        assert "User Memory Context" in context or "No prior memory" in context
