# Async and Sync APIs

## Async (recommended)

Mnemo is async-first.  Use it inside any `async def` function:

```python
async with MemoryStore(backend=InMemoryBackend()) as store:
    mid = await store.add(Memory(content="hello"))
```

It is built on [AnyIO](https://anyio.readthedocs.io/), so it works equally
well with asyncio and Trio event loops.

## Sync shim

If you cannot use `async`/`await` (Django views, CLI scripts, Jupyter without
`%autoawait`), use `SyncMemoryStore`:

```python
from mnemo.store import SyncMemoryStore
from mnemo.backends import InMemoryBackend
from mnemo.types import Memory, MemoryQuery

with SyncMemoryStore(backend=InMemoryBackend()) as store:
    mid = store.add(Memory(content="hello"))
    results = store.search(MemoryQuery(text="hello"))
```

!!! warning
    `SyncMemoryStore` starts a **new event loop** per call via `anyio.run()`.
    Do **not** call it from inside a running async event loop — use the async
    API instead.  For mixed codebases, consider
    [`asyncer.syncify`](https://asyncer.tiangolo.com/) which bridges into a
    background thread pool.
