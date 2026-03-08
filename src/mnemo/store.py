"""High-level MemoryStore: the primary user-facing API.

Async/sync dual-API pattern
---------------------------
``MemoryStore`` is async-first.  Every public method is a coroutine.
For callers in a synchronous context we expose a thin ``SyncMemoryStore``
wrapper that uses ``anyio.from_thread.run_sync`` / ``anyio.run`` to bridge
into the async layer without the user needing to manage an event loop.

The pattern here follows the recommendation in Seth Larson's
"Designing Libraries for Async and Sync I/O":

1. The *real* implementation lives in the async class.
2. The sync wrapper is a thin shim — it does NOT duplicate logic.
3. We accept AnyIO so both asyncio and Trio users work out of the box.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import anyio

if TYPE_CHECKING:
    from mnemo.protocols import MemoryBackend
    from mnemo.types import Memory, MemoryQuery, MemoryResult


class MemoryStore:
    """Async-first, backend-agnostic memory store.

    Args:
        backend: Any object satisfying the :class:`~mnemo.protocols.MemoryBackend`
            protocol.

    Example:
        >>> async def main():
        ...     async with MemoryStore(backend=InMemoryBackend()) as store:
        ...         mid = await store.add(Memory(content="hello world"))
        ...         result = await store.get(mid)
    """

    def __init__(self, backend: MemoryBackend) -> None:
        self._backend = backend

    # ------------------------------------------------------------------
    # Lifecycle — async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> MemoryStore:
        """Enter the async context manager."""
        return self

    async def __aexit__(self, *_: object) -> None:
        """Exit the async context manager and close the store."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying backend and release all resources."""
        await self._backend.aclose()

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def add(self, memory: Memory) -> str:
        """Add a memory to the store.

        Args:
            memory: The memory to persist.

        Returns:
            The unique ID assigned to the stored memory.
        """
        return await self._backend.add(memory)

    async def get(self, memory_id: str) -> Memory | None:
        """Retrieve a memory by ID.

        Args:
            memory_id: The ID returned by :meth:`add`.

        Returns:
            The memory, or ``None`` if not found.
        """
        return await self._backend.get(memory_id)

    async def search(self, query: MemoryQuery) -> list[MemoryResult]:
        """Search memories by semantic similarity and/or metadata filters.

        Args:
            query: A :class:`~mnemo.types.MemoryQuery` describing what to find.

        Returns:
            A ranked list of :class:`~mnemo.types.MemoryResult` objects.
        """
        return await self._backend.search(query)

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID.

        Args:
            memory_id: The ID to remove.

        Returns:
            ``True`` if deleted, ``False`` if not found.
        """
        return await self._backend.delete(memory_id)


# ---------------------------------------------------------------------------
# Synchronous shim — zero logic duplication
# ---------------------------------------------------------------------------


class SyncMemoryStore:
    """Synchronous façade over :class:`MemoryStore`.

    Intended for callers that cannot use ``async``/``await`` (e.g., Jupyter
    cells in ``%autoawait off`` mode, Django views, CLI scripts).

    Internally this wraps every call with ``anyio.run()``, so it is
    compatible with both asyncio and Trio backends.

    Args:
        backend: Any object satisfying :class:`~mnemo.protocols.MemoryBackend`.

    Example:
        >>> store = SyncMemoryStore(backend=InMemoryBackend())
        >>> with store:
        ...     mid = store.add(Memory(content="hello"))
        ...     mem = store.get(mid)
    """

    def __init__(self, backend: MemoryBackend) -> None:
        self._async_store = MemoryStore(backend)

    def __enter__(self) -> SyncMemoryStore:
        """Enter the sync context manager."""
        return self

    def __exit__(self, *_: object) -> None:
        """Exit the sync context manager and close the store."""
        self.close()

    def close(self) -> None:
        """Close the underlying backend."""
        anyio.run(self._async_store.aclose)

    def add(self, memory: Memory) -> str:
        """Synchronous version of :meth:`MemoryStore.add`."""
        return anyio.run(self._async_store.add, memory)

    def get(self, memory_id: str) -> Memory | None:
        """Synchronous version of :meth:`MemoryStore.get`."""
        return anyio.run(self._async_store.get, memory_id)

    def search(self, query: MemoryQuery) -> list[MemoryResult]:
        """Synchronous version of :meth:`MemoryStore.search`."""
        return anyio.run(self._async_store.search, query)

    def delete(self, memory_id: str) -> bool:
        """Synchronous version of :meth:`MemoryStore.delete`."""
        return anyio.run(self._async_store.delete, memory_id)
