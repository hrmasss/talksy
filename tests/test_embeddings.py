"""Tests for the multi-provider embeddings factory.

Verifies that ``get_embeddings()`` returns the correct provider based on
the ``EMBEDDING_PROVIDER`` setting (openai / google / huggingface).

No real API calls are made - tests patch the settings and check the
returned class type.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestEmbeddingFactory:
    """Verify ``get_embeddings()`` dispatches to the right provider."""

    def _get_fresh(self):
        """Import and clear the lru_cache so each test starts clean."""
        import app.memory.client as mod
        mod.get_embeddings.cache_clear()
        return mod

    def test_openai_provider(self):
        mod = self._get_fresh()
        with patch.object(mod, "settings") as s:
            s.embedding_provider = "openai"
            s.openai_api_key = "sk-test"
            s.openrouter_api_key = ""
            s.embedding_model = "text-embedding-3-small"
            emb = mod.get_embeddings()
        from langchain_openai import OpenAIEmbeddings
        assert isinstance(emb, OpenAIEmbeddings)
        mod.get_embeddings.cache_clear()

    def test_google_provider(self):
        mod = self._get_fresh()
        with patch.object(mod, "settings") as s:
            s.embedding_provider = "google"
            s.gemini_api_key = "fake-gemini-key"
            s.embedding_model = "models/embedding-001"
            emb = mod.get_embeddings()
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        assert isinstance(emb, GoogleGenerativeAIEmbeddings)
        mod.get_embeddings.cache_clear()

    def test_huggingface_provider(self):
        """Verify HF provider path is called correctly (model download mocked)."""
        mod = self._get_fresh()

        from unittest.mock import MagicMock

        mock_hf_cls = MagicMock()
        mock_hf_instance = MagicMock()
        mock_hf_cls.return_value = mock_hf_instance

        with (
            patch.object(mod, "settings") as s,
            patch(
                "langchain_huggingface.HuggingFaceEmbeddings",
                mock_hf_cls,
            ),
        ):
            mod.get_embeddings.cache_clear()
            s.embedding_provider = "huggingface"
            s.huggingface_embedding_model = (
                "sentence-transformers/all-MiniLM-L6-v2"
            )
            emb = mod.get_embeddings()

        assert emb is mock_hf_instance
        mock_hf_cls.assert_called_once_with(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
        )
        mod.get_embeddings.cache_clear()

    def test_unknown_provider_raises(self):
        mod = self._get_fresh()
        with (
            patch.object(mod, "settings") as s,
            pytest.raises(ValueError, match="Unknown embedding_provider"),
        ):
            s.embedding_provider = "nonexistent"
            mod.get_embeddings()
        mod.get_embeddings.cache_clear()

    def test_openai_missing_key_raises(self):
        mod = self._get_fresh()
        with (
            patch.object(mod, "settings") as s,
            pytest.raises(ValueError, match="OPENAI_API_KEY"),
        ):
            s.embedding_provider = "openai"
            s.openai_api_key = ""
            s.openrouter_api_key = ""
            mod.get_embeddings()
        mod.get_embeddings.cache_clear()


class TestEmbeddingDimensions:
    """Verify ``get_embedding_dim()`` returns correct sizes per model."""

    def test_openai_small(self):
        from app.memory.client import _EMBEDDING_DIMS
        assert _EMBEDDING_DIMS["text-embedding-3-small"] == 1536

    def test_huggingface_minilm(self):
        from app.memory.client import _EMBEDDING_DIMS
        assert _EMBEDDING_DIMS["sentence-transformers/all-MiniLM-L6-v2"] == 384

    def test_google_embedding(self):
        from app.memory.client import _EMBEDDING_DIMS
        assert _EMBEDDING_DIMS["models/embedding-001"] == 768
