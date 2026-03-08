# Quick Start

```python
import asyncio
from mnemo import MemoryStore
from mnemo.backends import InMemoryBackend
from mnemo.types import Memory, MemoryQuery

async def main() -> None:
    async with MemoryStore(backend=InMemoryBackend()) as store:
        # Add memories
        await store.add(Memory(content="Paris is the capital of France", metadata={"topic": "geography"}))
        await store.add(Memory(content="Berlin is the capital of Germany", metadata={"topic": "geography"}))

        # Semantic search (with the InMemoryBackend: substring match)
        results = await store.search(MemoryQuery(text="capital", limit=5))
        for r in results:
            print(f"[{r.score:.2f}] {r.memory.content}")

asyncio.run(main())
```
