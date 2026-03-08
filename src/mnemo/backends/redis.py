"""Redis Stack backend — persistent vector search via RediSearch."""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
import struct
import uuid
from typing import TYPE_CHECKING

from mnemo.protocols import BaseBackend
from mnemo.types import Memory, MemoryResult

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from mnemo.types import MemoryQuery

try:
    import redis.asyncio as aioredis
    from redis.commands.search.field import TextField, VectorField
    from redis.commands.search.index_definition import IndexDefinition, IndexType
    from redis.commands.search.query import Query
    from redis.exceptions import ResponseError
except ImportError as _exc:  # pragma: no cover
    raise ImportError(
        "RedisBackend requires the 'redis' extra: pip install 'mnemo[redis]'"
    ) from _exc

_FT_SPECIAL = re.compile(r'([,.<>{}\[\]"\':;!@#$%^&*()\-+=~])')


class RedisBackend(BaseBackend):
    """Production-grade backend using Redis Stack's RediSearch vector index.

    Memories are stored as Redis Hashes.  When an ``embed_fn`` is supplied,
    ``search`` performs cosine-similarity KNN via the HNSW index; otherwise it
    falls back to RediSearch full-text matching.

    Args:
        url: Redis connection URL (e.g. ``"redis://localhost:6379"``).
        index_name: RediSearch index name and key-prefix namespace.
        vector_dim: Dimensionality of embedding vectors (must match
            the output of ``embed_fn`` if provided).
        embed_fn: Async callable that converts a text string into a
            ``list[float]`` embedding.  When supplied, :meth:`add` will
            auto-embed memories that lack a pre-computed vector, and
            :meth:`search` will use KNN vector similarity.
        overwrite_index: Drop and recreate the RediSearch index on startup.
            Useful in tests or during schema migrations.

    Example:
        >>> import anyio
        >>> async def demo() -> None:
        ...     async with RedisBackend(url="redis://localhost:6379") as b:
        ...         mid = await b.add(Memory(content="hello Redis"))
        ...         mem = await b.get(mid)
        ...         assert mem is not None
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379",
        *,
        index_name: str = "mnemo",
        vector_dim: int = 1536,
        embed_fn: Callable[[str], Awaitable[list[float]]] | None = None,
        overwrite_index: bool = False,
    ) -> None:
        super().__init__()
        self._url = url
        self._index_name = index_name
        self._vector_dim = vector_dim
        self._embed_fn = embed_fn
        self._overwrite_index = overwrite_index
        self._client: aioredis.Redis = aioredis.from_url(url, decode_responses=False)
        self._initialized = False
        self._init_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Lazy initialisation
    # ------------------------------------------------------------------

    async def _ensure_ready(self) -> None:
        """Create the RediSearch index on first use (double-checked lock)."""
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            await self._setup_index()
            self._initialized = True

    async def _setup_index(self) -> None:
        """Create (or recreate) the RediSearch HNSW index."""
        ft = self._client.ft(self._index_name)
        if self._overwrite_index:
            with contextlib.suppress(ResponseError):
                await ft.dropindex(delete_documents=False)
        schema = [
            TextField("content"),
            VectorField(
                "embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": str(self._vector_dim),
                    "DISTANCE_METRIC": "COSINE",
                },
            ),
        ]
        prefix = f"{self._index_name}:mem:"
        # Index already exists — safe to ignore on reconnect
        with contextlib.suppress(ResponseError):
            await ft.create_index(
                schema,
                definition=IndexDefinition(  # type: ignore[no-untyped-call]
                    prefix=[prefix], index_type=IndexType.HASH
                ),
            )

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    def _memory_key(self, memory_id: str) -> str:
        """Return the Redis Hash key for *memory_id*."""
        return f"{self._index_name}:mem:{memory_id}"

    @staticmethod
    def _escape_ft(text: str) -> str:
        """Escape RediSearch special characters for full-text queries."""
        return _FT_SPECIAL.sub(r"\\\1", text)

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def _decode_memory(self, data: dict[bytes, bytes]) -> Memory:
        """Reconstruct a :class:`~mnemo.types.Memory` from raw Redis Hash data."""
        content = data[b"content"].decode()
        memory_id = data[b"memory_id"].decode()
        metadata: dict[str, object] = json.loads(data.get(b"metadata", b"{}"))
        raw_emb = data.get(b"embedding")
        embedding: list[float] | None = None
        if raw_emb:
            n = len(raw_emb) // 4
            embedding = list(struct.unpack(f"{n}f", raw_emb))
        return Memory(
            content=content,
            metadata=metadata,
            embedding=embedding,
            memory_id=memory_id,
        )

    # ------------------------------------------------------------------
    # MemoryBackend protocol
    # ------------------------------------------------------------------

    async def add(self, memory: Memory) -> str:
        """Persist a memory and return its assigned ID.

        If ``embed_fn`` was supplied and *memory* carries no pre-computed
        embedding, the content is embedded automatically before storage.

        Args:
            memory: The memory object to store.

        Returns:
            A unique identifier string for the stored memory.
        """
        self._check_not_closed()
        await self._ensure_ready()
        mid = memory.memory_id or str(uuid.uuid4())
        embedding = memory.embedding
        if embedding is None and self._embed_fn is not None:
            embedding = await self._embed_fn(memory.content)
        if embedding is not None and len(embedding) != self._vector_dim:
            raise ValueError(
                f"Embedding dimension {len(embedding)} does not match "
                f"index dimension {self._vector_dim}."
            )
        mapping: dict[str | bytes, str | bytes | float | int] = {
            "content": memory.content,
            "memory_id": mid,
            "metadata": json.dumps(memory.metadata),
        }
        if embedding is not None:
            mapping["embedding"] = struct.pack(f"{len(embedding)}f", *embedding)
        await self._client.hset(self._memory_key(mid), mapping=mapping)  # type: ignore[misc]
        return mid

    async def get(self, memory_id: str) -> Memory | None:
        """Retrieve a single memory by its ID.

        Args:
            memory_id: The unique identifier returned by :meth:`add`.

        Returns:
            The memory if found, otherwise ``None``.
        """
        self._check_not_closed()
        data: dict[bytes, bytes] = await self._client.hgetall(  # type: ignore[misc]
            self._memory_key(memory_id)
        )
        if not data:
            return None
        return self._decode_memory(data)

    async def search(self, query: MemoryQuery) -> list[MemoryResult]:
        """Return memories ranked by relevance to the query.

        Uses KNN vector search when an ``embed_fn`` was provided at
        construction; otherwise falls back to RediSearch full-text matching.

        Args:
            query: Structured query containing text, filters, and limit.

        Returns:
            A list of results ordered by descending relevance score.
        """
        self._check_not_closed()
        await self._ensure_ready()
        if self._embed_fn is not None:
            return await self._vector_search(query)
        return await self._fulltext_search(query)

    async def delete(self, memory_id: str) -> bool:
        """Remove a memory by ID.

        Args:
            memory_id: The ID to delete.

        Returns:
            ``True`` if the memory existed and was removed, ``False``
            if it was not found.
        """
        self._check_not_closed()
        count: int = await self._client.delete(self._memory_key(memory_id))
        return count > 0

    async def aclose(self) -> None:
        """Close the Redis connection and mark the backend as closed."""
        self._closed = True
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Search implementations
    # ------------------------------------------------------------------

    async def _vector_search(self, query: MemoryQuery) -> list[MemoryResult]:
        """KNN search using the HNSW cosine index."""
        assert self._embed_fn is not None  # guarded by caller
        query_vec = await self._embed_fn(query.text)
        vec_bytes = struct.pack(f"{len(query_vec)}f", *query_vec)
        # Over-fetch to leave headroom for metadata post-filtering.
        k = max(query.limit * 4, 100)
        q = (
            Query(f"*=>[KNN {k} @embedding $vec AS vector_score]")
            .sort_by("vector_score")
            .return_fields("content", "metadata", "memory_id", "vector_score")
            .paging(0, k)
            .dialect(2)
        )
        raw = await self._client.ft(self._index_name).search(
            q, query_params={"vec": vec_bytes}
        )
        results: list[MemoryResult] = []
        for doc in raw.docs:
            # redis-py returns "N/A" (not None) for missing hash fields.
            raw_meta = getattr(doc, "metadata", None)
            meta_str = (
                raw_meta if isinstance(raw_meta, str) and raw_meta != "N/A" else "{}"
            )
            try:
                metadata: dict[str, object] = json.loads(meta_str)
            except (json.JSONDecodeError, ValueError):
                metadata = {}
            if not all(metadata.get(k) == v for k, v in query.filters.items()):
                continue
            # COSINE distance ∈ [0, 2]; clamp converted score to [0.0, 1.0].
            raw_dist = getattr(doc, "vector_score", None)
            try:
                if raw_dist is not None and raw_dist != "N/A":
                    distance = float(raw_dist)
                else:
                    distance = 1.0
            except (ValueError, TypeError):
                distance = 1.0
            score = max(0.0, 1.0 - distance)
            if score < query.score_threshold:
                continue
            mem = Memory(
                content=getattr(doc, "content", ""),
                metadata=metadata,
                memory_id=getattr(doc, "memory_id", ""),
            )
            results.append(MemoryResult(memory=mem, score=score))
            if len(results) >= query.limit:
                break
        return results

    async def _fulltext_search(self, query: MemoryQuery) -> list[MemoryResult]:
        """Full-text fallback search (no embed_fn configured)."""
        escaped = self._escape_ft(query.text)
        over_limit = query.limit * 4
        try:
            q = (
                Query(f"@content:(*{escaped}*)")
                .return_fields("content", "metadata", "memory_id")
                .paging(0, over_limit)
                .dialect(2)
            )
            raw = await self._client.ft(self._index_name).search(q)
        except ResponseError:
            return []
        results: list[MemoryResult] = []
        # Use the same scoring convention as InMemoryBackend for consistency.
        score = 0.5
        if score < query.score_threshold:
            return []
        for doc in raw.docs:
            raw_meta = getattr(doc, "metadata", None)
            meta_str = (
                raw_meta if isinstance(raw_meta, str) and raw_meta != "N/A" else "{}"
            )
            try:
                metadata: dict[str, object] = json.loads(meta_str)
            except (json.JSONDecodeError, ValueError):
                metadata = {}
            if not all(metadata.get(k) == v for k, v in query.filters.items()):
                continue
            mem = Memory(
                content=getattr(doc, "content", ""),
                metadata=metadata,
                memory_id=getattr(doc, "memory_id", ""),
            )
            results.append(MemoryResult(memory=mem, score=score))
            if len(results) >= query.limit:
                break
        return results
