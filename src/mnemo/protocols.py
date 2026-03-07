"""Core Protocol definitions for the mnemo plugin interface.

Design rationale
----------------
We use ``Protocol`` (PEP 544) for the *external* plugin boundary so that
third-party backends never need to import from ``mnemo`` at all — they just
need to satisfy the structural shape.  This avoids a circular import trap and
keeps the barrier to writing a custom backend as low as possible.

We use ``ABC`` only for the *internal* ``BaseBackend`` helper class that
provides shared validation + lifecycle logic that concrete backends inherit.
Third-party authors CAN subclass it for convenience, but they are not
required to.

Runtime checking via ``@runtime_checkable`` is intentionally kept on the
Protocol so you can do ``isinstance(obj, MemoryBackend)`` in tests.
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence

    from mnemo.types import Memory, MemoryQuery, MemoryResult


# ---------------------------------------------------------------------------
# Core Protocol — the only contract a backend must satisfy
# ---------------------------------------------------------------------------


@runtime_checkable
class MemoryBackend(Protocol):
    """Structural interface for all mnemo storage backends.

    Implementors do NOT need to inherit from this class.  A class satisfies
    this protocol if it defines all methods with the matching signatures.

    Args:
        Protocol: Python's built-in structural typing base.

    Example:
        >>> class MyBackend:
        ...     async def add(self, memory: Memory) -> str: ...
        ...     async def get(self, memory_id: str) -> Memory | None: ...
        ...     async def search(self, query: MemoryQuery) -> list[MemoryResult]: ...
        ...     async def delete(self, memory_id: str) -> bool: ...
        ...     async def aclose(self) -> None: ...
        >>> isinstance(MyBackend(), MemoryBackend)
        True
    """

    async def add(self, memory: Memory) -> str:
        """Persist a memory and return its assigned ID.

        Args:
            memory: The memory object to store.

        Returns:
            A unique identifier string for the stored memory.
        """
        ...

    async def get(self, memory_id: str) -> Memory | None:
        """Retrieve a single memory by its ID.

        Args:
            memory_id: The unique identifier returned by :meth:`add`.

        Returns:
            The memory if found, otherwise ``None``.
        """
        ...

    async def search(self, query: MemoryQuery) -> list[MemoryResult]:
        """Return memories ranked by relevance to the query.

        Args:
            query: Structured query containing text, filters, and limit.

        Returns:
            A list of results ordered by descending relevance score.
        """
        ...

    async def delete(self, memory_id: str) -> bool:
        """Remove a memory by ID.

        Args:
            memory_id: The ID to delete.

        Returns:
            ``True`` if the memory existed and was removed, ``False``
            if it was not found.
        """
        ...

    async def aclose(self) -> None:
        """Release all resources held by the backend.

        Called automatically when used as an async context manager.
        """
        ...


# ---------------------------------------------------------------------------
# Optional enrichment Protocols — backends implement these for extra features
# ---------------------------------------------------------------------------


class SupportsStreaming(Protocol):
    """Optional protocol for backends that can stream search results."""

    def stream_search(
        self, query: MemoryQuery
    ) -> AsyncIterator[MemoryResult]:
        """Yield results one at a time as they become available.

        Args:
            query: Structured query.

        Yields:
            Individual memory results in relevance order.
        """
        ...


class SupportsBulkOperations(Protocol):
    """Optional protocol for backends with efficient batch APIs."""

    async def add_many(self, memories: Sequence[Memory]) -> list[str]:
        """Persist multiple memories atomically.

        Args:
            memories: An ordered sequence of memories to store.

        Returns:
            A list of IDs in the same order as the input.
        """
        ...

    async def delete_many(self, memory_ids: Sequence[str]) -> int:
        """Delete multiple memories in one operation.

        Args:
            memory_ids: IDs to remove.

        Returns:
            The count of successfully deleted memories.
        """
        ...


# ---------------------------------------------------------------------------
# Internal abstract base — use this inside mnemo for shared logic
# ---------------------------------------------------------------------------


class BaseBackend(abc.ABC):
    """Internal ABC for backends shipped with mnemo.

    Third-party backends are NOT required to inherit from this class;
    they only need to satisfy :class:`MemoryBackend`.  This class exists
    to centralise validation, lifecycle hooks, and telemetry for the
    first-party backends.
    """

    def __init__(self, **kwargs: Any) -> None:
        self._closed = False

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    async def __aenter__(self) -> BaseBackend:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    def _check_not_closed(self) -> None:
        if self._closed:
            raise RuntimeError(
                f"{type(self).__name__} has been closed and cannot be reused."
            )

    @abc.abstractmethod
    async def aclose(self) -> None:
        """Release resources.  Subclasses must call ``self._closed = True``."""
        ...

    # ------------------------------------------------------------------
    # Required backend methods — all abstract
    # ------------------------------------------------------------------

    @abc.abstractmethod
    async def add(self, memory: Memory) -> str: ...

    @abc.abstractmethod
    async def get(self, memory_id: str) -> Memory | None: ...

    @abc.abstractmethod
    async def search(self, query: MemoryQuery) -> list[MemoryResult]: ...

    @abc.abstractmethod
    async def delete(self, memory_id: str) -> bool: ...
