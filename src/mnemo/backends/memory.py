"""In-memory backend — useful for tests and prototyping."""

from __future__ import annotations

import uuid
from typing import Any

from mnemo.protocols import BaseBackend
from mnemo.types import Memory, MemoryQuery, MemoryResult


class InMemoryBackend(BaseBackend):
    """A non-persistent in-process backend backed by a plain dict.

    Thread-safe reads are fine; this backend is *not* designed for
    concurrent writes across OS threads.

    Example:
        >>> import anyio
        >>> async def demo():
        ...     async with InMemoryBackend() as backend:
        ...         mid = await backend.add(Memory(content="hello"))
        ...         mem = await backend.get(mid)
        ...         assert mem is not None
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._store: dict[str, Memory] = {}

    async def add(self, memory: Memory) -> str:
        self._check_not_closed()
        mid = memory.memory_id or str(uuid.uuid4())
        # Store a fresh copy with the assigned ID
        self._store[mid] = Memory(
            content=memory.content,
            metadata=memory.metadata,
            embedding=memory.embedding,
            memory_id=mid,
        )
        return mid

    async def get(self, memory_id: str) -> Memory | None:
        self._check_not_closed()
        return self._store.get(memory_id)

    async def search(self, query: MemoryQuery) -> list[MemoryResult]:
        """Naïve substring search — replace with vector similarity in real backends."""
        self._check_not_closed()
        results: list[MemoryResult] = []
        for memory in self._store.values():
            # Apply metadata filters
            if not all(
                memory.metadata.get(k) == v for k, v in query.filters.items()
            ):
                continue
            # Naïve scoring: 1.0 if substring match, 0.5 otherwise
            score = 1.0 if query.text.lower() in memory.content.lower() else 0.5
            if score >= query.score_threshold:
                results.append(MemoryResult(memory=memory, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[: query.limit]

    async def delete(self, memory_id: str) -> bool:
        self._check_not_closed()
        return self._store.pop(memory_id, None) is not None

    async def aclose(self) -> None:
        self._store.clear()
        self._closed = True
