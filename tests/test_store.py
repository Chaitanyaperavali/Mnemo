"""Tests for MemoryStore and InMemoryBackend."""

from __future__ import annotations

import pytest

from mnemo.backends.memory import InMemoryBackend
from mnemo.protocols import MemoryBackend
from mnemo.store import MemoryStore
from mnemo.types import Memory, MemoryQuery


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_in_memory_backend_satisfies_protocol() -> None:
    """InMemoryBackend must satisfy the MemoryBackend protocol at runtime."""
    assert isinstance(InMemoryBackend(), MemoryBackend)


# ---------------------------------------------------------------------------
# CRUD round-trips
# ---------------------------------------------------------------------------


async def test_add_and_get(memory_store: MemoryStore) -> None:
    mem = Memory(content="The capital of France is Paris.")
    mid = await memory_store.add(mem)
    assert isinstance(mid, str)

    retrieved = await memory_store.get(mid)
    assert retrieved is not None
    assert retrieved.content == mem.content
    assert retrieved.memory_id == mid


async def test_get_missing_returns_none(memory_store: MemoryStore) -> None:
    result = await memory_store.get("does-not-exist")
    assert result is None


async def test_delete_existing(memory_store: MemoryStore) -> None:
    mid = await memory_store.add(Memory(content="ephemeral"))
    deleted = await memory_store.delete(mid)
    assert deleted is True
    assert await memory_store.get(mid) is None


def test_delete_missing_returns_false(memory_store: MemoryStore) -> None:  # type: ignore[misc]
    # We need an event loop; use pytest-asyncio's auto mode
    pass  # see async variant below


async def test_delete_missing(memory_store: MemoryStore) -> None:
    deleted = await memory_store.delete("ghost-id")
    assert deleted is False


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


async def test_search_finds_matching_content(memory_store: MemoryStore) -> None:
    await memory_store.add(Memory(content="Python is a great language"))
    await memory_store.add(Memory(content="Rust is fast"))

    query = MemoryQuery(text="Python", limit=5)
    results = await memory_store.search(query)

    assert len(results) >= 1
    top = results[0]
    assert "Python" in top.memory.content
    assert top.score == pytest.approx(1.0)


async def test_search_metadata_filter(memory_store: MemoryStore) -> None:
    await memory_store.add(
        Memory(content="fact A", metadata={"source": "web"})
    )
    await memory_store.add(
        Memory(content="fact B", metadata={"source": "book"})
    )

    query = MemoryQuery(text="fact", filters={"source": "book"})
    results = await memory_store.search(query)

    assert all(r.memory.metadata["source"] == "book" for r in results)


async def test_search_respects_limit(memory_store: MemoryStore) -> None:
    for i in range(10):
        await memory_store.add(Memory(content=f"memory {i}"))

    results = await memory_store.search(MemoryQuery(text="memory", limit=3))
    assert len(results) <= 3


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


async def test_context_manager_closes_backend() -> None:
    backend = InMemoryBackend()
    async with MemoryStore(backend=backend) as store:
        await store.add(Memory(content="temporary"))
    assert backend._closed is True


@pytest.mark.slow()
async def test_large_store_performance(memory_store: MemoryStore) -> None:
    """Adding 1000 memories should complete in well under 30 s."""
    for i in range(1000):
        await memory_store.add(Memory(content=f"entry {i}"))
    results = await memory_store.search(MemoryQuery(text="entry 999"))
    assert any("999" in r.memory.content for r in results)
