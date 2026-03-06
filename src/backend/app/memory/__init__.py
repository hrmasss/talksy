"""Long-term memory module backed by Qdrant vector database.

Provides per-user, per-category memory storage and retrieval so that
agents can track user progress over time and personalise their responses.
"""

from .client import get_embeddings, get_qdrant_client
from .models import MemoryCategory, MemoryEntry, MemorySearchResult
from .service import MemoryService, memory_service
from .tools import (
    get_user_progress_summary,
    recall_user_memory,
    store_user_memory,
)

__all__ = [
    "MemoryCategory",
    "MemoryEntry",
    "MemorySearchResult",
    "MemoryService",
    "get_embeddings",
    "get_qdrant_client",
    "get_user_progress_summary",
    "memory_service",
    "recall_user_memory",
    "store_user_memory",
]
