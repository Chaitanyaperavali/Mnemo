# Mnemo

**LLM agent memory orchestration library.**

Mnemo provides a backend-agnostic, async-first API for storing, retrieving,
and managing memories for LLM agents.

## Features

- Async-first design with a thin sync shim for non-async callers
- Backend-agnostic via `Protocol` — bring your own vector store
- Typed from top to bottom (`py.typed` marker, strict mypy)
- Ships with an in-memory backend for tests and prototyping

## Quick example

```python
import asyncio
from mnemo import MemoryStore
from mnemo.backends import InMemoryBackend
from mnemo.types import Memory, MemoryQuery

async def main() -> None:
    async with MemoryStore(backend=InMemoryBackend()) as store:
        mid = await store.add(Memory(content="Paris is the capital of France"))
        results = await store.search(MemoryQuery(text="capital of France"))
        print(results[0].memory.content)

asyncio.run(main())
```
