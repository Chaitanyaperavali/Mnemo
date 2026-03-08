# Writing a Custom Backend

Any class satisfying the `MemoryBackend` Protocol can be used as a backend.
You do **not** need to import or subclass anything from `mnemo`.

```python
from mnemo.types import Memory, MemoryQuery, MemoryResult


class MyRedisBackend:
    """Example custom backend — satisfies MemoryBackend structurally."""

    def __init__(self, url: str) -> None:
        import redis.asyncio as redis
        self._client = redis.from_url(url)

    async def add(self, memory: Memory) -> str:
        import uuid, json
        mid = memory.memory_id or str(uuid.uuid4())
        await self._client.set(mid, json.dumps({"content": memory.content, "meta": memory.metadata}))
        return mid

    async def get(self, memory_id: str) -> Memory | None:
        import json
        raw = await self._client.get(memory_id)
        if raw is None:
            return None
        data = json.loads(raw)
        return Memory(content=data["content"], metadata=data["meta"], memory_id=memory_id)

    async def search(self, query: MemoryQuery) -> list[MemoryResult]:
        # Production: use Redis Search / vector similarity here
        return []

    async def delete(self, memory_id: str) -> bool:
        return bool(await self._client.delete(memory_id))

    async def aclose(self) -> None:
        await self._client.aclose()
```

Then pass it to `MemoryStore`:

```python
from mnemo import MemoryStore

store = MemoryStore(backend=MyRedisBackend("redis://localhost:6379"))
```

!!! tip "Runtime protocol check"
    You can verify your backend satisfies the protocol at runtime:
    ```python
    from mnemo.protocols import MemoryBackend
    assert isinstance(MyRedisBackend("redis://localhost"), MemoryBackend)
    ```
