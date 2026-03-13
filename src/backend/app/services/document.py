"""Document processing service for admin document uploads."""

import os
import tempfile
from enum import Enum
from typing import Any

import anyio
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.models import Distance, VectorParams

from app.core.logging import logger
from app.memory.client import (
    collection_name_for,
    get_embedding_dim,
    get_embeddings,
    get_qdrant_client,
)


class KnowledgeBaseCategory(str, Enum):
    """Allowed top-level knowledge base categories for admin uploads."""

    EXAM = "exam"
    DAILY_STUDY = "daily_study"
    ROADMAP = "roadmap"
    CUSTOM = "custom"


class KnowledgeBaseExamSection(str, Enum):
    """Allowed IELTS exam section categories."""

    SPEAKING = "speaking"
    WRITING = "writing"
    READING = "reading"
    LISTENING = "listening"


def _slugify_collection_part(value: str) -> str:
    """Normalize free-text collection segments to snake_case."""
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_")


def resolve_collection_suffix(
    *,
    collection_name: str | None = None,
    category: str | None = None,
    exam_section: str | None = None,
    custom_collection_name: str | None = None,
) -> str:
    """Resolve and validate a collection suffix from category inputs.

    Supports both legacy `collection_name` and structured category params.
    """
    if category is None:
        if collection_name is None or not collection_name.strip():
            return "knowledge_base"
        return _slugify_collection_part(collection_name) or "knowledge_base"

    try:
        category_enum = KnowledgeBaseCategory(category)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in KnowledgeBaseCategory)
        raise ValueError(
            f"Invalid category '{category}'. Allowed values: {allowed}"
        ) from exc

    if category_enum == KnowledgeBaseCategory.EXAM:
        section_val = exam_section or KnowledgeBaseExamSection.SPEAKING.value
        try:
            section_enum = KnowledgeBaseExamSection(section_val)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in KnowledgeBaseExamSection)
            raise ValueError(
                f"Invalid exam_section '{section_val}'. Allowed values: {allowed}"
            ) from exc
        return f"kb_exam_{section_enum.value}"

    if category_enum == KnowledgeBaseCategory.DAILY_STUDY:
        return "kb_daily_study"

    if category_enum == KnowledgeBaseCategory.ROADMAP:
        return "kb_roadmap"

    custom_name = custom_collection_name or collection_name or ""
    return _slugify_collection_part(custom_name) or "knowledge_base"


def build_collection_metadata(
    *,
    collection_suffix: str,
    category: str | None = None,
    exam_section: str | None = None,
    source_file_name: str | None = None,
) -> dict[str, Any]:
    """Build metadata tags attached to each stored chunk."""
    payload: dict[str, Any] = {
        "kb_collection_suffix": collection_suffix,
    }
    if category:
        payload["kb_category"] = category
    if exam_section:
        payload["kb_exam_section"] = exam_section
    if source_file_name:
        payload["source_file_name"] = source_file_name
    return payload


def process_pdf_and_store(
    file_bytes: bytes,
    collection_suffix: str,
    metadata_tags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Process a PDF, chunk it, and store in a given Qdrant collection."""
    # Write bytes to temp file since PyPDFLoader requires a file path
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        # Load PDF
        loader = PyPDFLoader(tmp_path)
        docs = loader.load()
        
        # Split text
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        splits = text_splitter.split_documents(docs)
        
        if not splits:
            return {"status": "error", "message": "No text extracted from PDF."}

        # Initialize Qdrant and Embeddings
        client = get_qdrant_client()
        embeddings = get_embeddings()
        dim = get_embedding_dim()
        
        collection_name = collection_name_for(collection_suffix)
        
        # Ensure collection exists
        try:
            client.get_collection(collection_name)
        except Exception:
            logger.info(f"Creating collection {collection_name}")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            
        # Extract texts and generate embeddings
        texts = [doc.page_content for doc in splits]
        metadatas = [doc.metadata for doc in splits]
        if metadata_tags:
            metadatas = [{**md, **metadata_tags} for md in metadatas]
        
        from langchain_qdrant import QdrantVectorStore
        
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings
        )
        
        vector_store.add_texts(texts=texts, metadatas=metadatas)
        
        return {
            "status": "success",
            "message": f"Successfully processed and stored {len(splits)} chunks.",
            "collection": collection_name,
            "chunks_count": len(splits)
        }
        
    finally:
        os.remove(tmp_path)


async def async_process_pdf_and_store(file_bytes: bytes, collection_suffix: str) -> None:
    """Run process_pdf_and_store in a background thread."""
    try:
        await anyio.to_thread.run_sync(
            process_pdf_and_store, file_bytes, collection_suffix
        )
        logger.info(f"Background PDF processing completed for {collection_suffix}")
    except Exception as e:
        logger.error(f"Background PDF processing failed: {e}")


async def async_process_pdf_and_store_with_metadata(
    file_bytes: bytes,
    collection_suffix: str,
    metadata_tags: dict[str, Any] | None = None,
) -> None:
    """Run PDF processing in a background thread with metadata tags."""
    try:
        await anyio.to_thread.run_sync(
            process_pdf_and_store, file_bytes, collection_suffix, metadata_tags
        )
        logger.info(f"Background PDF processing completed for {collection_suffix}")
    except Exception as e:
        logger.error(f"Background PDF processing failed: {e}")


def retrieve_from_collection(
    collection_suffix: str,
    query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve chunks from a specific Qdrant collection using vector search."""
    client = get_qdrant_client()
    embeddings = get_embeddings()
    collection_name = collection_name_for(collection_suffix)
    
    # Check if collection exists
    try:
        client.get_collection(collection_name)
    except Exception:
        return []

    from langchain_qdrant import QdrantVectorStore
    
    # We can reconstruct vector store using existing client
    qdrant = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings
    )
    
    results = qdrant.similarity_search(query, k=limit)
    return [
        {"content": doc.page_content, "metadata": doc.metadata}
        for doc in results
    ]
