"""Built-in backend implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mnemo.backends.memory import InMemoryBackend

if TYPE_CHECKING:
    from mnemo.backends.redis import RedisBackend

__all__ = ["InMemoryBackend", "RedisBackend"]


def __getattr__(name: str) -> object:
    """Lazily import RedisBackend to avoid hard dependency on redis package."""
    if name == "RedisBackend":
        from mnemo.backends.redis import RedisBackend

        return RedisBackend
    raise AttributeError(name)
