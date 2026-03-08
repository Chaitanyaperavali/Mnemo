"""Mnemo — LLM agent memory orchestration library.

Provides a backend-agnostic, async-first API for storing, retrieving,
and managing memories for LLM agents.

Example:
    >>> from mnemo import MemoryStore
    >>> store = MemoryStore(backend=InMemoryBackend())
"""

from mnemo._version import __version__
from mnemo.store import MemoryStore

__all__ = ["MemoryStore", "__version__"]
