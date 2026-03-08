# Mnemo

> Multi-tier memory orchestration for LLM agents.

Mnemo is a backend-agnostic, async-first Python library for storing, retrieving, and searching memories in LLM agent pipelines. Swap backends without changing application code.

## Installation

```bash
pip install mnemo
# or with uv:
uv add mnemo
```

### Optional backend extras

```bash
pip install "mnemo[redis]"      # Redis backend
pip install "mnemo[pgvector]"   # PostgreSQL + pgvector backend
pip install "mnemo[openai]"     # OpenAI embeddings support
```

## Quick start

```python
import asyncio
from mnemo import MemoryStore
from mnemo.backends import InMemoryBackend
from mnemo.types import Memory, MemoryQuery

async def main() -> None:
    async with MemoryStore(backend=InMemoryBackend()) as store:
        await store.add(Memory(content="Paris is the capital of France", metadata={"topic": "geography"}))
        await store.add(Memory(content="Berlin is the capital of Germany", metadata={"topic": "geography"}))

        results = await store.search(MemoryQuery(text="capital", limit=5))
        for r in results:
            print(f"[{r.score:.2f}] {r.memory.content}")

asyncio.run(main())
```

### Synchronous API

```python
from mnemo.store import SyncMemoryStore
from mnemo.backends import InMemoryBackend
from mnemo.types import Memory, MemoryQuery

with SyncMemoryStore(backend=InMemoryBackend()) as store:
    mid = store.add(Memory(content="hello"))
    results = store.search(MemoryQuery(text="hello"))
```

## Custom backends

Any class satisfying the `MemoryBackend` protocol works — no inheritance required:

```python
from mnemo import MemoryStore
from mnemo.types import Memory, MemoryQuery, MemoryResult

class MyBackend:
    async def add(self, memory: Memory) -> str: ...
    async def get(self, memory_id: str) -> Memory | None: ...
    async def search(self, query: MemoryQuery) -> list[MemoryResult]: ...
    async def delete(self, memory_id: str) -> bool: ...
    async def aclose(self) -> None: ...

store = MemoryStore(backend=MyBackend())
```

## Links

- [Documentation](https://yourorg.github.io/mnemo)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)

## License

Apache License 2.0
