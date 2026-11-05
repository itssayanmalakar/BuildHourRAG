from __future__ import annotations

from typing import Protocol

from mf_facts.contracts import Chunk, RetrievedChunk


class VectorStore(Protocol):
    def ensure_collection(self, dim: int, distance: str, reset: bool) -> None: ...

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...

    def search(self, vector: list[float], k: int,
               filters: dict | None = None) -> list[RetrievedChunk]: ...

    def count(self) -> int: ...

    def all_chunks(self) -> list[Chunk]: ...
