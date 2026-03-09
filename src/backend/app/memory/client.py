"""Qdrant client and multi-provider embeddings factory.

Supports **Google Generative AI** and **HuggingFace** embeddings.
The active provider is chosen via ``EMBEDDING_PROVIDER``
in settings (``google`` | ``huggingface``).
"""

from __future__ import annotations

from functools import lru_cache

from app.config import settings
from langchain_core.embeddings import Embeddings
from qdrant_client import QdrantClient

# Provider-specific dimension defaults
_EMBEDDING_DIMS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "models/embedding-001": 768,
    "models/text-embedding-004": 768,
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-mpnet-base-v2": 768,
    "BAAI/bge-small-en-v1.5": 384,
}


def get_embedding_dim() -> int:
    """Return the vector dimension for the currently configured model."""
    model = settings.embedding_model
    if settings.embedding_provider == "huggingface":
        model = settings.huggingface_embedding_model
    return _EMBEDDING_DIMS.get(model, settings.qdrant_embedding_dim)


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

@lru_cache
def get_embeddings() -> Embeddings:
    """Return a cached embeddings instance based on ``EMBEDDING_PROVIDER``.

    * ``google``      - uses ``langchain_google_genai.GoogleGenerativeAIEmbeddings``
    * ``huggingface`` - uses ``langchain_huggingface.HuggingFaceEmbeddings`` (local)
    """
    provider = settings.embedding_provider

    if provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        from app.agents.common.llm import next_api_key

        api_key = next_api_key()
        return GoogleGenerativeAIEmbeddings(
            model=settings.embedding_model,
            google_api_key=api_key,
        )

    if provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=settings.huggingface_embedding_model,
        )

    raise ValueError(f"Unknown embedding_provider: '{provider}'")


# ---------------------------------------------------------------------------
# Qdrant client
# ---------------------------------------------------------------------------

@lru_cache
def get_qdrant_client() -> QdrantClient:
    """Return a cached Qdrant client instance."""
    kwargs: dict = {"url": settings.qdrant_url, "timeout": 30}
    if settings.qdrant_api_key:
        kwargs["api_key"] = settings.qdrant_api_key
    return QdrantClient(**kwargs)


def collection_name_for(suffix: str = "memory") -> str:
    """Build a fully-qualified Qdrant collection name."""
    return f"{settings.qdrant_collection_prefix}_{suffix}"
