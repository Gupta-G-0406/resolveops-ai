
"""Local ChromaDB store for ResolveOps policy retrieval."""

import logging
import os
import threading
import time

from functools import lru_cache
from pathlib import Path

import chromadb

from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction,
)

from dotenv import load_dotenv


# --------------------------------------------------
# Environment and logging
# --------------------------------------------------

load_dotenv()

logger = logging.getLogger("resolveops.policy_store")

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Prevent concurrent collection initialization.
_collection_lock = threading.Lock()


# --------------------------------------------------
# Logging helper
# --------------------------------------------------

def log_step(message: str, started: float) -> None:
    """Log elapsed time for a policy store operation."""

    logger.info(
        "[POLICY STORE] %s | elapsed=%.2fs | thread=%s",
        message,
        time.perf_counter() - started,
        threading.current_thread().name,
    )


# --------------------------------------------------
# Thread-safe collection access
# --------------------------------------------------

def get_collection():
    """
    Return the cached ChromaDB policy collection.

    The lock ensures that only one thread initializes
    the collection at a time.

    Once initialized, the cached collection is reused.
    """

    with _collection_lock:
        return _get_collection_cached()


# --------------------------------------------------
# Cached collection initialization
# --------------------------------------------------

@lru_cache(maxsize=1)
def _get_collection_cached():
    """
    Initialize the persistent ChromaDB collection.

    This function should be called through
    get_collection() rather than directly.
    """

    total_started = time.perf_counter()

    logger.info(
        "[RAG PROFILE] Collection initialization started"
    )

    # ----------------------------------------------
    # Step 1: Resolve ChromaDB storage path
    # ----------------------------------------------

    raw_path = Path(
        os.getenv(
            "CHROMA_PATH",
            "./data/chroma",
        )
    )

    chroma_path = (
        raw_path
        if raw_path.is_absolute()
        else BACKEND_DIR / raw_path
    )

    chroma_path = chroma_path.resolve()

    logger.info(
        "[RAG PROFILE] ChromaDB path=%s",
        chroma_path,
    )

    # ----------------------------------------------
    # Step 2: Initialize persistent ChromaDB client
    # ----------------------------------------------

    step_started = time.perf_counter()

    client = chromadb.PersistentClient(
        path=str(chroma_path)
    )

    logger.warning(
        "[RAG PROFILE] PersistentClient "
        "duration_seconds=%.2f",
        time.perf_counter() - step_started,
    )

    # ----------------------------------------------
    # Step 3: Initialize embedding model
    # ----------------------------------------------

    model_name = os.getenv(
        "EMBEDDING_MODEL",
        "all-MiniLM-L6-v2",
    )

    step_started = time.perf_counter()

    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name=model_name
    )

    logger.warning(
        "[RAG PROFILE] Embedding model "
        "duration_seconds=%.2f model=%s",
        time.perf_counter() - step_started,
        model_name,
    )

    # ----------------------------------------------
    # Step 4: Open or create policy collection
    # ----------------------------------------------

    collection_name = os.getenv(
        "POLICY_COLLECTION",
        "resolveops_policies",
    )

    step_started = time.perf_counter()

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
    )

    logger.warning(
        "[RAG PROFILE] Collection opening "
        "duration_seconds=%.2f",
        time.perf_counter() - step_started,
    )

    # ----------------------------------------------
    # Step 5: Initialization complete
    # ----------------------------------------------

    logger.warning(
        "[RAG PROFILE] Total get_collection "
        "duration_seconds=%.2f",
        time.perf_counter() - total_started,
    )

    return collection


# --------------------------------------------------
# Policy similarity search
# --------------------------------------------------

def search_policies(
    query: str,
    limit: int = 3,
) -> list[dict]:
    """
    Search company policies using ChromaDB.

    Returns matching policies with:
    - policy_id
    - title
    - category
    - content
    - distance
    """

    started = time.perf_counter()

    # ----------------------------------------------
    # Step 1: Validate search query
    # ----------------------------------------------

    if not isinstance(query, str) or not query.strip():
        logger.warning(
            "[POLICY STORE] Empty policy search query"
        )
        return []

    query = query.strip()

    # Restrict result count to 1-5.
    limit = max(1, min(int(limit), 5))

    log_step(
        "Policy search started",
        started,
    )

    # ----------------------------------------------
    # Step 2: Get cached collection
    # ----------------------------------------------

    collection = get_collection()

    log_step(
        "Collection acquired",
        started,
    )

    # ----------------------------------------------
    # Step 3: Check available policies
    # ----------------------------------------------

    total = collection.count()

    logger.info(
        "[POLICY STORE] Policies available=%d",
        total,
    )

    if total == 0:
        logger.warning(
            "[POLICY STORE] Policy collection is empty"
        )
        return []

    # ----------------------------------------------
    # Step 4: Execute vector similarity search
    # ----------------------------------------------

    query_started = time.perf_counter()

    results = collection.query(
        query_texts=[query],
        n_results=min(limit, total),
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    logger.info(
        "[RAG PROFILE] Policy query "
        "duration_seconds=%.2f",
        time.perf_counter() - query_started,
    )

    # ----------------------------------------------
    # Step 5: Parse ChromaDB results
    # ----------------------------------------------

    matches = []

    ids = (results.get("ids") or [[]])[0]
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    for doc_id, content, metadata, distance in zip(
        ids,
        documents,
        metadatas,
        distances,
    ):
        metadata = metadata or {}

        matches.append(
            {
                "policy_id": doc_id,
                "title": metadata.get("title", ""),
                "category": metadata.get("category", ""),
                "content": content,
                "distance": distance,
            }
        )

    # ----------------------------------------------
    # Step 6: Return matching policies
    # ----------------------------------------------

    logger.info(
        "[POLICY STORE] Search completed "
        "matches=%d duration_seconds=%.2f",
        len(matches),
        time.perf_counter() - started,
    )

    return matches
