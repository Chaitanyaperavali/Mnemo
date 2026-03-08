"""Shared pytest fixtures for the mnemo test suite."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

from mnemo.backends.memory import InMemoryBackend
from mnemo.store import MemoryStore

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests on asyncio (override per test with @pytest.mark.anyio)."""
    return "asyncio"


@pytest_asyncio.fixture()
async def memory_backend() -> AsyncIterator[InMemoryBackend]:
    """Yield a fresh InMemoryBackend, closing it after the test."""
    async with InMemoryBackend() as backend:
        yield backend


@pytest_asyncio.fixture()
async def memory_store(memory_backend: InMemoryBackend) -> MemoryStore:
    """Yield a MemoryStore wired to the in-memory backend."""
    return MemoryStore(backend=memory_backend)
