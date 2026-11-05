from __future__ import annotations

import chromadb

from mf_facts.contracts import Chunk, RetrievedChunk

META_FIELDS = (
    "doc_id", "url", "title", "amc", "scheme", "doc_type",
    "section", "fact_type", "is_atomic", "fetched_at", "content_hash",
)


class ChromaStore:
    def __init__(self, persist_dir: str, collection: str):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.name = collection
        self.col = None

    def ensure_collection(self, dim: int, distance: str, reset: bool = False) -> None:
        if reset:
            try:
                self.client.delete_collection(self.name)
            except Exception:
                pass
        try:
            self.col = self.client.get_or_create_collection(
                name=self.name,
                metadata={"hnsw:space": distance},
                embedding_function=None,
            )
        except Exception:
            # chromadb >= 1.x configuration form
            self.col = self.client.get_or_create_collection(
                name=self.name,
                configuration={"hnsw": {"space": distance}},
                embedding_function=None,
            )

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        assert self.col is not None, "call ensure_collection first"
        for i in range(0, len(chunks), 100):
            bc = chunks[i:i + 100]
            self.col.upsert(
                ids=[c.chunk_id for c in bc],
                embeddings=vectors[i:i + 100],
                documents=[c.text for c in bc],
                metadatas=[self._meta(c) for c in bc],
            )

    @staticmethod
    def _meta(c: Chunk) -> dict:
        d = c.model_dump(mode="json")
        out: dict = {}
        for k in META_FIELDS:
            v = d[k]
            if v is None:
                out[k] = ""
            elif k == "is_atomic":
                out[k] = int(v)
            else:
                out[k] = v
        return out

    @staticmethod
    def _to_chunk(cid: str, meta: dict, text: str = "") -> Chunk:
        return Chunk(
            chunk_id=cid, doc_id=meta["doc_id"], url=meta["url"],
            title=meta["title"], amc=meta["amc"], scheme=meta["scheme"],
            doc_type=meta["doc_type"], section=meta["section"],
            fact_type=meta["fact_type"] or None,
            is_atomic=bool(meta["is_atomic"]), text=text, token_count=0,
            fetched_at=meta["fetched_at"], content_hash=meta["content_hash"],
        )

    def search(self, vector: list[float], k: int,
               filters: dict | None = None) -> list[RetrievedChunk]:
        assert self.col is not None, "call ensure_collection first"
        where = None
        if filters:
            parts = []
            for key, val in filters.items():
                if isinstance(val, list):
                    parts.append({key: {"$in": val}})
                elif val:
                    parts.append({key: {"$eq": val}})
            if len(parts) == 1:
                where = parts[0]
            elif parts:
                where = {"$and": parts}

        res = self.col.query(
            query_embeddings=[vector], n_results=k, where=where,
            include=["documents", "metadatas", "distances"],
        )
        out: list[RetrievedChunk] = []
        for cid, meta, text, dist in zip(
            res["ids"][0], res["metadatas"][0],
            res["documents"][0], res["distances"][0],
        ):
            out.append(RetrievedChunk(
                chunk=self._to_chunk(cid, meta, text or ""),
                score=1.0 - float(dist),
                source="dense",
            ))
        return out

    def count(self) -> int:
        assert self.col is not None, "call ensure_collection first"
        return int(self.col.count())

    def all_chunks(self) -> list[Chunk]:
        assert self.col is not None, "call ensure_collection first"
        res = self.col.get(include=["documents", "metadatas"])
        out: list[Chunk] = []
        for cid, text, meta in zip(res["ids"], res["documents"], res["metadatas"]):
            out.append(self._to_chunk(cid, meta, text or ""))
        return out
