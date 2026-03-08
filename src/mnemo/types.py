"""Shared domain types for mnemo.

All types are plain dataclasses or TypedDicts so that backends can import
them without pulling in heavy dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _str_object_dict() -> dict[str, object]:
    return {}


@dataclass(frozen=True, slots=True)
class Memory:
    """An immutable memory record.

    Args:
        content: The raw text (or serialised) content of the memory.
        metadata: Arbitrary key-value pairs attached to this memory.
        embedding: Optional pre-computed embedding vector.
        memory_id: Optional caller-supplied ID; backends may override it.
    """

    content: str
    metadata: dict[str, object] = field(default_factory=_str_object_dict)
    embedding: list[float] | None = None
    memory_id: str | None = None


@dataclass(frozen=True, slots=True)
class MemoryQuery:
    """A structured search query.

    Args:
        text: Natural-language text to search for.
        filters: Key-value metadata filters (AND logic).
        limit: Maximum number of results to return.
        score_threshold: Minimum similarity score (0.0-1.0).
    """

    text: str
    filters: dict[str, object] = field(default_factory=_str_object_dict)
    limit: int = 10
    score_threshold: float = 0.0


@dataclass(frozen=True, slots=True)
class MemoryResult:
    """A search result pairing a memory with its relevance score.

    Args:
        memory: The retrieved memory.
        score: Similarity score in the range [0.0, 1.0].
    """

    memory: Memory
    score: float
