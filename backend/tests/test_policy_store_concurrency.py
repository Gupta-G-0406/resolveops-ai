
"""Tests for thread-safe policy collection initialization."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

from app.rag import policy_store


def test_concurrent_collection_initialization(monkeypatch):
    """Concurrent calls must initialize the collection once."""

    policy_store._get_collection_cached.cache_clear()

    initialization_count = 0
    count_lock = threading.Lock()

    fake_collection = MagicMock()
    fake_client = MagicMock()
    fake_client.get_or_create_collection.return_value = (
        fake_collection
    )

    def fake_persistent_client(*args, **kwargs):
        nonlocal initialization_count

        with count_lock:
            initialization_count += 1

        time.sleep(0.05)
        return fake_client

    monkeypatch.setattr(
        policy_store.chromadb,
        "PersistentClient",
        fake_persistent_client,
    )

    monkeypatch.setattr(
        policy_store,
        "SentenceTransformerEmbeddingFunction",
        lambda **kwargs: MagicMock(),
    )

    try:
        with ThreadPoolExecutor(max_workers=10) as executor:
            collections = list(
                executor.map(
                    lambda _: policy_store.get_collection(),
                    range(10),
                )
            )

        assert initialization_count == 1
        assert all(
            collection is fake_collection
            for collection in collections
        )

    finally:
        policy_store._get_collection_cached.cache_clear()


def test_failed_initialization_can_retry(monkeypatch):
    """A failed initialization must not be cached."""

    policy_store._get_collection_cached.cache_clear()

    calls = 0
    fake_collection = MagicMock()
    fake_client = MagicMock()
    fake_client.get_or_create_collection.return_value = (
        fake_collection
    )

    def fake_persistent_client(*args, **kwargs):
        nonlocal calls
        calls += 1

        if calls == 1:
            raise RuntimeError("Temporary ChromaDB failure")

        return fake_client

    monkeypatch.setattr(
        policy_store.chromadb,
        "PersistentClient",
        fake_persistent_client,
    )

    monkeypatch.setattr(
        policy_store,
        "SentenceTransformerEmbeddingFunction",
        lambda **kwargs: MagicMock(),
    )

    try:
        try:
            policy_store.get_collection()
        except RuntimeError:
            pass
        else:
            raise AssertionError(
                "Expected initialization failure"
            )

        collection = policy_store.get_collection()

        assert collection is fake_collection
        assert calls == 2

    finally:
        policy_store._get_collection_cached.cache_clear()
