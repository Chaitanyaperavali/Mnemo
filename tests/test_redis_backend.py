"""Integration and unit tests for RedisBackend."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

from mnemo.backends.redis import RedisBackend
from mnemo.protocols import MemoryBackend
from mnemo.types import Memory, MemoryQuery

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

pytestmark = [pytest.mark.integration, pytest.mark.backend("redis")]

_REDIS_URL = "redis://localhost:6379"
_INDEX = "mnemo_test"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def redis_backend() -> AsyncIterator[RedisBackend]:
    """Yield a RedisBackend wired to a local Redis Stack; skip if unavailable."""
    try:
        import redis.asyncio as aioredis

        client: aioredis.Redis[bytes] = aioredis.from_url(_REDIS_URL)
        await client.ping()
        await client.aclose()
    except Exception:
        pytest.skip("Redis Stack not available at redis://localhost:6379")

    async with RedisBackend(
        url=_REDIS_URL,
        index_name=_INDEX,
        overwrite_index=True,
    ) as backend:
        yield backend


@pytest_asyncio.fixture()
async def redis_backend_with_embed() -> AsyncIterator[RedisBackend]:
    """RedisBackend with a simple stub embed_fn (unit-vector per char-code)."""
    try:
        import redis.asyncio as aioredis

        client: aioredis.Redis[bytes] = aioredis.from_url(_REDIS_URL)
        await client.ping()
        await client.aclose()
    except Exception:
        pytest.skip("Redis Stack not available at redis://localhost:6379")

    dim = 4

    async def _stub_embed(text: str) -> list[float]:
        """Deterministic stub: project first *dim* char-codes to unit vector."""
        codes = [float(ord(c)) for c in (text + "\0" * dim)[:dim]]
        norm = sum(x * x for x in codes) ** 0.5 or 1.0
        return [x / norm for x in codes]

    async with RedisBackend(
        url=_REDIS_URL,
        index_name=f"{_INDEX}_vec",
        vector_dim=dim,
        embed_fn=_stub_embed,
        overwrite_index=True,
    ) as backend:
        yield backend


# ---------------------------------------------------------------------------
# Protocol conformance (no network required)
# ---------------------------------------------------------------------------


def test_redis_backend_satisfies_protocol() -> None:
    """RedisBackend must satisfy MemoryBackend at runtime (structural check)."""
    assert isinstance(RedisBackend(), MemoryBackend)


# ---------------------------------------------------------------------------
# CRUD round-trips
# ---------------------------------------------------------------------------


async def test_add_and_get(redis_backend: RedisBackend) -> None:
    mem = Memory(content="The Eiffel Tower is in Paris.")
    mid = await redis_backend.add(mem)
    assert isinstance(mid, str)
    assert mid

    retrieved = await redis_backend.get(mid)
    assert retrieved is not None
    assert retrieved.content == mem.content
    assert retrieved.memory_id == mid


async def test_add_preserves_caller_id(redis_backend: RedisBackend) -> None:
    mem = Memory(content="fixed ID test", memory_id="my-custom-id")
    mid = await redis_backend.add(mem)
    assert mid == "my-custom-id"
    result = await redis_backend.get("my-custom-id")
    assert result is not None
    assert result.memory_id == "my-custom-id"


async def test_add_preserves_metadata(redis_backend: RedisBackend) -> None:
    mem = Memory(content="meta test", metadata={"source": "web", "year": 2024})
    mid = await redis_backend.add(mem)
    result = await redis_backend.get(mid)
    assert result is not None
    assert result.metadata["source"] == "web"
    assert result.metadata["year"] == 2024


async def test_get_missing_returns_none(redis_backend: RedisBackend) -> None:
    result = await redis_backend.get("does-not-exist")
    assert result is None


async def test_delete_existing(redis_backend: RedisBackend) -> None:
    mid = await redis_backend.add(Memory(content="ephemeral"))
    deleted = await redis_backend.delete(mid)
    assert deleted is True
    assert await redis_backend.get(mid) is None


async def test_delete_missing_returns_false(redis_backend: RedisBackend) -> None:
    deleted = await redis_backend.delete("ghost-id")
    assert deleted is False


# ---------------------------------------------------------------------------
# Full-text search (no embed_fn)
# ---------------------------------------------------------------------------


async def test_search_fulltext_finds_match(redis_backend: RedisBackend) -> None:
    await redis_backend.add(Memory(content="Python is a great language"))
    await redis_backend.add(Memory(content="Rust is fast and memory-safe"))

    results = await redis_backend.search(MemoryQuery(text="Python", limit=5))
    assert len(results) >= 1
    assert any("Python" in r.memory.content for r in results)


async def test_search_metadata_filter(redis_backend: RedisBackend) -> None:
    await redis_backend.add(Memory(content="fact A", metadata={"source": "web"}))
    await redis_backend.add(Memory(content="fact B", metadata={"source": "book"}))

    results = await redis_backend.search(
        MemoryQuery(text="fact", filters={"source": "book"})
    )
    assert results
    assert all(r.memory.metadata["source"] == "book" for r in results)


async def test_search_respects_limit(redis_backend: RedisBackend) -> None:
    for i in range(10):
        await redis_backend.add(Memory(content=f"memory item {i}"))

    results = await redis_backend.search(MemoryQuery(text="memory", limit=3))
    assert len(results) <= 3


async def test_search_score_threshold_filters(redis_backend: RedisBackend) -> None:
    await redis_backend.add(Memory(content="threshold test content"))
    # Full-text results score at 0.5; threshold above that → empty list.
    results = await redis_backend.search(
        MemoryQuery(text="threshold", score_threshold=0.9)
    )
    assert results == []


# ---------------------------------------------------------------------------
# Vector search (with embed_fn)
# ---------------------------------------------------------------------------


async def test_search_vector_returns_results(
    redis_backend_with_embed: RedisBackend,
) -> None:
    await redis_backend_with_embed.add(Memory(content="alpha"))
    await redis_backend_with_embed.add(Memory(content="beta"))

    results = await redis_backend_with_embed.search(MemoryQuery(text="alpha", limit=5))
    assert len(results) >= 1
    assert all(0.0 <= r.score <= 1.0 for r in results)


async def test_search_vector_metadata_filter(
    redis_backend_with_embed: RedisBackend,
) -> None:
    await redis_backend_with_embed.add(Memory(content="vec A", metadata={"tag": "x"}))
    await redis_backend_with_embed.add(Memory(content="vec B", metadata={"tag": "y"}))

    results = await redis_backend_with_embed.search(
        MemoryQuery(text="vec", filters={"tag": "y"}, limit=10)
    )
    assert results
    assert all(r.memory.metadata["tag"] == "y" for r in results)


async def test_add_auto_embeds_missing_vector(
    redis_backend_with_embed: RedisBackend,
) -> None:
    """add() should embed content when memory has no pre-computed vector."""
    mem = Memory(content="auto-embed me", embedding=None)
    mid = await redis_backend_with_embed.add(mem)
    stored = await redis_backend_with_embed.get(mid)
    assert stored is not None
    # The stored memory should now carry the auto-embedded vector.
    assert stored.embedding is not None
    assert len(stored.embedding) == 4


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


async def test_context_manager_closes_backend() -> None:
    try:
        import redis.asyncio as aioredis

        client: aioredis.Redis[bytes] = aioredis.from_url(_REDIS_URL)
        await client.ping()
        await client.aclose()
    except Exception:
        pytest.skip("Redis Stack not available at redis://localhost:6379")

    backend = RedisBackend(url=_REDIS_URL, index_name=f"{_INDEX}_lifecycle")
    async with backend:
        await backend.add(Memory(content="temporary"))
    assert backend._closed is True


async def test_use_after_close_raises(redis_backend: RedisBackend) -> None:
    await redis_backend.aclose()
    with pytest.raises(RuntimeError, match="closed"):
        await redis_backend.add(Memory(content="should fail"))
