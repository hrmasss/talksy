"""Core memory service - store, search, delete, and summarise user memories.

All Qdrant interactions are encapsulated here so the rest of the app
(agents, API routes, tools) only depend on this high-level interface.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from app.core.logging import logger
from qdrant_client import models as qmodels

from .client import collection_name_for, get_embedding_dim, get_embeddings, get_qdrant_client
from .models import (
    MemoryCategory,
    MemoryEntry,
    MemorySearchResult,
    UserProgressSummary,
)

# Default collection used for all long-term memories
_COLLECTION = collection_name_for("memory")


class MemoryService:
    """Async-friendly service for user long-term memory backed by Qdrant."""

    # ------------------------------------------------------------------
    # Collection bootstrap
    # ------------------------------------------------------------------

    def _ensure_collection(self) -> None:
        """Create the Qdrant collection if it doesn't exist yet."""
        client = get_qdrant_client()
        existing = [c.name for c in client.get_collections().collections]
        if _COLLECTION not in existing:
            client.create_collection(
                collection_name=_COLLECTION,
                vectors_config=qmodels.VectorParams(
                    size=get_embedding_dim(),
                    distance=qmodels.Distance.COSINE,
                ),
            )
            # Payload indices for fast filtering
            for field in ("user_id", "category", "importance"):
                client.create_payload_index(
                    collection_name=_COLLECTION,
                    field_name=field,
                    field_schema=(
                        qmodels.PayloadSchemaType.KEYWORD
                        if field != "importance"
                        else qmodels.PayloadSchemaType.FLOAT
                    ),
                )
            logger.info(f"Created Qdrant collection '{_COLLECTION}'")

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    async def _bg_store(self, entry: MemoryEntry) -> None:
        """Background task to embed and store a single memory entry."""
        try:
            embeddings = get_embeddings()
            vector = await embeddings.aembed_query(entry.content)

            client = get_qdrant_client()
            client.upsert(
                collection_name=_COLLECTION,
                points=[
                    qmodels.PointStruct(
                        id=entry.id,
                        vector=vector,
                        payload=entry.to_qdrant_payload(),
                    )
                ],
            )
            logger.debug(
                f"Background-stored memory id={entry.id} user={entry.user_id} cat={entry.category.value}"
            )
        except Exception:
            logger.exception(f"Failed to background-store memory {entry.id}")

    async def _bg_store_many(self, entries: Sequence[MemoryEntry]) -> None:
        """Background task to embed and store multiple memory entries."""
        try:
            embeddings = get_embeddings()
            texts = [e.content for e in entries]
            vectors = await embeddings.aembed_documents(texts)

            points = [
                qmodels.PointStruct(
                    id=entry.id,
                    vector=vec,
                    payload=entry.to_qdrant_payload(),
                )
                for entry, vec in zip(entries, vectors, strict=False)
            ]

            client = get_qdrant_client()
            client.upsert(collection_name=_COLLECTION, points=points)
            logger.debug(f"Background-batch-stored {len(points)} memories")
        except Exception:
            logger.exception(f"Failed to background-batch-store {len(entries)} memories")

    async def store(
        self,
        *,
        user_id: str,
        category: MemoryCategory | str,
        content: str,
        metadata: dict[str, Any] | None = None,
        importance: float = 0.5,
        memory_id: str | None = None,
    ) -> MemoryEntry:
        """Create a :class:`MemoryEntry` and schedule background storage in Qdrant.

        Returns the created :class:`MemoryEntry` immediately.
        """
        self._ensure_collection()

        if isinstance(category, str):
            category = MemoryCategory(category)

        entry = MemoryEntry(
            id=memory_id or uuid.uuid4().hex,
            user_id=user_id,
            category=category,
            content=content,
            metadata=metadata or {},
            importance=importance,
        )

        # Schedule background storage
        asyncio.create_task(self._bg_store(entry))

        return entry

    async def store_many(
        self,
        entries: Sequence[MemoryEntry],
    ) -> list[MemoryEntry]:
        """Schedule background batch-storage of multiple memory entries."""
        self._ensure_collection()
        
        # Schedule background storage
        asyncio.create_task(self._bg_store_many(entries))
        
        return list(entries)

    # ------------------------------------------------------------------
    # Search / recall
    # ------------------------------------------------------------------

    async def search(
        self,
        *,
        user_id: str,
        query: str,
        category: MemoryCategory | str | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
        importance_gte: float | None = None,
    ) -> list[MemorySearchResult]:
        """Semantic search over a user's memories.

        Parameters
        ----------
        user_id:        Only return memories belonging to this user.
        query:          Natural-language query to embed and search with.
        category:       Optional category filter.
        top_k:          Max results to return.
        min_score:      Minimum cosine similarity threshold.
        importance_gte: Only return memories with importance >= this value.
        """
        self._ensure_collection()

        # Build Qdrant filter
        must_conditions: list[qmodels.FieldCondition] = [
            qmodels.FieldCondition(
                key="user_id",
                match=qmodels.MatchValue(value=user_id),
            )
        ]

        if category is not None:
            cat_val = category.value if isinstance(category, MemoryCategory) else category
            must_conditions.append(
                qmodels.FieldCondition(
                    key="category",
                    match=qmodels.MatchValue(value=cat_val),
                )
            )

        if importance_gte is not None:
            must_conditions.append(
                qmodels.FieldCondition(
                    key="importance",
                    range=qmodels.Range(gte=importance_gte),
                )
            )

        embeddings = get_embeddings()
        query_vector = await embeddings.aembed_query(query)

        client = get_qdrant_client()
        results = client.query_points(
            collection_name=_COLLECTION,
            query=query_vector,
            query_filter=qmodels.Filter(must=must_conditions),
            limit=top_k,
            score_threshold=min_score or None,
            with_payload=True,
        )

        memories: list[MemorySearchResult] = []
        for point in results.points:
            payload = point.payload or {}
            entry = MemoryEntry(
                id=point.id if isinstance(point.id, str) else str(point.id),
                user_id=payload.get("user_id", user_id),
                category=MemoryCategory(payload.get("category", "user_activity")),
                content=payload.get("content", ""),
                importance=payload.get("importance", 0.5),
                metadata={
                    k: v
                    for k, v in payload.items()
                    if k not in {
                        "user_id", "category", "content",
                        "importance", "created_at", "updated_at",
                    }
                },
                created_at=(
                    datetime.fromisoformat(payload["created_at"])
                    if "created_at" in payload
                    else datetime.now(UTC)
                ),
                updated_at=(
                    datetime.fromisoformat(payload["updated_at"])
                    if "updated_at" in payload
                    else datetime.now(UTC)
                ),
            )
            memories.append(
                MemorySearchResult(entry=entry, score=point.score)
            )

        return memories

    # ------------------------------------------------------------------
    # Retrieve by filters (no embedding needed)
    # ------------------------------------------------------------------

    async def get_by_category(
        self,
        *,
        user_id: str,
        category: MemoryCategory | str,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """Return the most recent memories for a user + category (no semantic query)."""
        self._ensure_collection()

        cat_val = category.value if isinstance(category, MemoryCategory) else category

        client = get_qdrant_client()
        results = client.scroll(
            collection_name=_COLLECTION,
            scroll_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="user_id",
                        match=qmodels.MatchValue(value=user_id),
                    ),
                    qmodels.FieldCondition(
                        key="category",
                        match=qmodels.MatchValue(value=cat_val),
                    ),
                ]
            ),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        entries: list[MemoryEntry] = []
        for point in results[0]:  # scroll returns (points, next_offset)
            payload = point.payload or {}
            entries.append(
                MemoryEntry(
                    id=point.id if isinstance(point.id, str) else str(point.id),
                    user_id=payload.get("user_id", user_id),
                    category=MemoryCategory(payload.get("category", cat_val)),
                    content=payload.get("content", ""),
                    importance=payload.get("importance", 0.5),
                    metadata={
                        k: v
                        for k, v in payload.items()
                        if k not in {
                            "user_id", "category", "content",
                            "importance", "created_at", "updated_at",
                        }
                    },
                    created_at=(
                        datetime.fromisoformat(payload["created_at"])
                        if "created_at" in payload
                        else datetime.now(UTC)
                    ),
                    updated_at=(
                        datetime.fromisoformat(payload["updated_at"])
                        if "updated_at" in payload
                        else datetime.now(UTC)
                    ),
                )
            )
        return entries

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete(self, *, memory_id: str) -> bool:
        """Delete a single memory by its ID."""
        client = get_qdrant_client()
        client.delete(
            collection_name=_COLLECTION,
            points_selector=qmodels.PointIdsList(points=[memory_id]),
        )
        logger.debug(f"Deleted memory id={memory_id}")
        return True

    async def delete_user_memories(
        self,
        *,
        user_id: str,
        category: MemoryCategory | str | None = None,
    ) -> int:
        """Delete all memories for a user, optionally filtered by category.

        Returns the (approximate) number of deleted points.
        """
        must: list[qmodels.FieldCondition] = [
            qmodels.FieldCondition(
                key="user_id",
                match=qmodels.MatchValue(value=user_id),
            )
        ]
        if category is not None:
            cat_val = category.value if isinstance(category, MemoryCategory) else category
            must.append(
                qmodels.FieldCondition(
                    key="category",
                    match=qmodels.MatchValue(value=cat_val),
                )
            )

        client = get_qdrant_client()

        # Count first so we can report deletions
        count = client.count(
            collection_name=_COLLECTION,
            count_filter=qmodels.Filter(must=must),
            exact=False,
        ).count

        client.delete(
            collection_name=_COLLECTION,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(must=must),
            ),
        )
        logger.info(f"Deleted ~{count} memories for user={user_id}")
        return count

    # ------------------------------------------------------------------
    # Progress summary
    # ------------------------------------------------------------------

    async def get_progress_summary(self, *, user_id: str) -> UserProgressSummary:
        """Build an aggregated progress snapshot for a user.

        Counts memories per category, pulls recent exam results, strengths,
        weaknesses, and goals.
        """
        self._ensure_collection()

        client = get_qdrant_client()

        # Total count for user
        total = client.count(
            collection_name=_COLLECTION,
            count_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="user_id",
                        match=qmodels.MatchValue(value=user_id),
                    )
                ]
            ),
            exact=False,
        ).count

        # Per-category counts
        cat_counts: dict[str, int] = {}
        # Skip categories that are commented out or shouldn't be tracked
        for cat in MemoryCategory:
            try:
                c = client.count(
                    collection_name=_COLLECTION,
                    count_filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="user_id",
                                match=qmodels.MatchValue(value=user_id),
                            ),
                            qmodels.FieldCondition(
                                key="category",
                                match=qmodels.MatchValue(value=cat.value),
                            ),
                        ]
                    ),
                    exact=False,
                ).count
                if c > 0:
                    cat_counts[cat.value] = c
            except ValueError:
                continue

        # Pull latest entries for specific categories
        exam_results = await self.get_by_category(
            user_id=user_id, category=MemoryCategory.EXAM_RESULT, limit=5
        )
        strengths_entries = await self.get_by_category(
            user_id=user_id, category=MemoryCategory.STRENGTH, limit=10
        )
        weaknesses_entries = await self.get_by_category(
            user_id=user_id, category=MemoryCategory.WEAKNESS, limit=10
        )
        goals_entries = await self.get_by_category(
            user_id=user_id, category=MemoryCategory.GOAL, limit=5
        )
        
        # Activity tracking is currently disabled
        # activity_entries = await self.get_by_category(
        #     user_id=user_id, category=MemoryCategory.USER_ACTIVITY, limit=1
        # )

        return UserProgressSummary(
            user_id=user_id,
            total_memories=total,
            categories=cat_counts,
            recent_exam_results=[
                {"content": e.content, **e.metadata} for e in exam_results
            ],
            strengths=[e.content for e in strengths_entries],
            weaknesses=[e.content for e in weaknesses_entries],
            goals=[e.content for e in goals_entries],
            latest_activity=None, # activity_entries[0].content if activity_entries else None,
        )

    # ------------------------------------------------------------------
    # Convenience helpers (used by exam_service, topic_service, etc.)
    # ------------------------------------------------------------------

    async def store_exam_result(
        self,
        *,
        user_id: str,
        section: str,
        band_score: float,
        strengths: list[str] | None = None,
        weaknesses: list[str] | None = None,
        recommendations: list[str] | None = None,
        report_summary: str = "",
        extra_metadata: dict[str, Any] | None = None,
    ) -> list[MemoryEntry]:
        """After an exam completes, schedule background storage for results and derived insights.

        Creates multiple memories:
        1. An ``EXAM_RESULT`` entry with the summary.
        2. Individual ``STRENGTH`` entries.
        3. Individual ``WEAKNESS`` entries.
        4. (Currently disabled: Activity log)
        """
        now = datetime.now(UTC)
        entries: list[MemoryEntry] = []

        # 1) Exam result summary
        content = (
            report_summary
            or f"Completed {section} exam with band score {band_score}."
        )
        entries.append(
            MemoryEntry(
                user_id=user_id,
                category=MemoryCategory.EXAM_RESULT,
                content=content,
                importance=0.9,
                metadata={
                    "section": section,
                    "band_score": band_score,
                    **(extra_metadata or {}),
                },
                created_at=now,
                updated_at=now,
            )
        )

        # 2) Strengths
        for s in (strengths or []):
            entries.append(
                MemoryEntry(
                    user_id=user_id,
                    category=MemoryCategory.STRENGTH,
                    content=s,
                    importance=0.7,
                    metadata={"section": section, "source": "exam"},
                    created_at=now,
                    updated_at=now,
                )
            )

        # 3) Weaknesses
        for w in (weaknesses or []):
            entries.append(
                MemoryEntry(
                    user_id=user_id,
                    category=MemoryCategory.WEAKNESS,
                    content=w,
                    importance=0.8,
                    metadata={"section": section, "source": "exam"},
                    created_at=now,
                    updated_at=now,
                )
            )

        # 4) Activity log (Currently disabled as requested)
        # entries.append(
        #     MemoryEntry(
        #         user_id=user_id,
        #         category=MemoryCategory.USER_ACTIVITY,
        #         content=f"User completed a {section} exam. Band score: {band_score}.",
        #         importance=0.5,
        #         metadata={"action": "exam_completed", "section": section, "band_score": band_score},
        #         created_at=now,
        #         updated_at=now,
        #     )
        # )

        # 5) Also store per-section category memory for targeted recall
        section_cat_map = {
            "speaking": MemoryCategory.SPEAKING,
            "writing": MemoryCategory.WRITING,
            "reading": MemoryCategory.READING,
            "listening": MemoryCategory.LISTENING,
        }
        if section in section_cat_map:
            detail_parts = []
            if strengths:
                detail_parts.append(f"Strengths: {', '.join(strengths)}")
            if weaknesses:
                detail_parts.append(f"Weaknesses: {', '.join(weaknesses)}")
            if recommendations:
                detail_parts.append(f"Recommendations: {', '.join(recommendations)}")
            detail = ". ".join(detail_parts) or content

            entries.append(
                MemoryEntry(
                    user_id=user_id,
                    category=section_cat_map[section],
                    content=f"Exam band {band_score}: {detail}",
                    importance=0.85,
                    metadata={"band_score": band_score, "source": "exam"},
                    created_at=now,
                    updated_at=now,
                )
            )

        return await self.store_many(entries)

    async def store_user_activity(
        self,
        *,
        user_id: str,
        action: str,
        detail: str = "",
        metadata: dict[str, Any] | None = None,
        importance: float = 0.4,
    ) -> MemoryEntry | None:
        """Quick helper to log a user activity. (Currently disabled as requested)"""
        logger.debug(f"User activity tracking is disabled. Skipping: {action}")
        return None

    async def recall_for_exam(
        self,
        *,
        user_id: str,
        section: str,
        query: str = "",
        top_k: int = 8,
    ) -> str:
        """Retrieve relevant memories for an exam session as a formatted string.

        Searches the section-specific category + weaknesses + strengths so the
        examiner agent can tailor questions & feedback.
        """
        combined: list[MemorySearchResult] = []

        search_query = query or f"User progress and performance in {section}"

        # Section-specific memories
        section_cat_map = {
            "speaking": MemoryCategory.SPEAKING,
            "writing": MemoryCategory.WRITING,
            "reading": MemoryCategory.READING,
            "listening": MemoryCategory.LISTENING,
        }
        if section in section_cat_map:
            combined.extend(
                await self.search(
                    user_id=user_id,
                    query=search_query,
                    category=section_cat_map[section],
                    top_k=top_k // 2,
                )
            )

        # Weaknesses relevant to this section
        combined.extend(
            await self.search(
                user_id=user_id,
                query=f"{section} weaknesses areas to improve",
                category=MemoryCategory.WEAKNESS,
                top_k=top_k // 4 or 2,
            )
        )

        # Strengths
        combined.extend(
            await self.search(
                user_id=user_id,
                query=f"{section} strengths",
                category=MemoryCategory.STRENGTH,
                top_k=top_k // 4 or 2,
            )
        )

        # Exam history
        combined.extend(
            await self.search(
                user_id=user_id,
                query=f"previous {section} exam results band score",
                category=MemoryCategory.EXAM_RESULT,
                top_k=3,
            )
        )

        if not combined:
            return "No prior memory found for this user."

        # De-duplicate by entry id and sort by score
        seen = set()
        unique = []
        for m in combined:
            if m.entry.id not in seen:
                seen.add(m.entry.id)
                unique.append(m)
        unique.sort(key=lambda m: m.score, reverse=True)

        lines = ["## User Memory Context"]
        for m in unique[:top_k]:
            lines.append(
                f"- [{m.entry.category.value}] (score={m.score:.2f}, "
                f"importance={m.entry.importance:.1f}): {m.entry.content}"
            )
        return "\n".join(lines)

    async def get_recent_exam_results(
        self,
        *,
        user_id: str,
        section: str,
        limit: int = 5,
    ) -> list[MemoryEntry]:
        """Return latest exam-result memories for a section (type) and user."""
        entries = await self.get_by_category(
            user_id=user_id,
            category=MemoryCategory.EXAM_RESULT,
            limit=max(limit * 4, 20),
        )

        section_key = section.strip().lower()
        filtered = [
            entry
            for entry in entries
            if str(entry.metadata.get("section", "")).strip().lower() == section_key
        ]

        filtered.sort(key=lambda e: e.created_at, reverse=True)
        return filtered[:limit]

    async def build_recent_exam_results_context(
        self,
        *,
        user_id: str,
        section: str,
        limit: int = 5,
    ) -> str:
        """Build a compact context block from top recent section exam results."""
        recent = await self.get_recent_exam_results(
            user_id=user_id,
            section=section,
            limit=limit,
        )
        if not recent:
            return ""

        lines = [f"## Top {len(recent)} Recent {section.title()} Exam Results"]
        for idx, item in enumerate(recent, start=1):
            band = item.metadata.get("band_score", "?")
            detail = item.content.strip().replace("\n", " ")
            lines.append(f"{idx}. Band {band}: {detail}")
        return "\n".join(lines)


# Module-level singleton
memory_service = MemoryService()
