from __future__ import annotations

import logging
from datetime import date

from mf_facts.contracts import RetrievedChunk
from mf_facts.retrieve.hybrid import BM25Index, fuse
from mf_facts.vectorstore.fingerprint import compute_fingerprint, read_fingerprint

log = logging.getLogger(__name__)


class Retriever:
    def __init__(self, settings, store, embedder, manifest=None):
        self.s = settings
        self.store = store
        self.embedder = embedder
        self.manifest = manifest
        self._chunks = store.all_chunks()
        self._by_id = {c.chunk_id: c for c in self._chunks}
        self._bm25 = BM25Index(self._chunks) if settings.retrieval.hybrid.enabled else None

    def assert_ready(self) -> None:
        if self.store.count() == 0:
            raise RuntimeError("vector index is empty — run `make build`")
        stored = read_fingerprint(self.s.phases.vectorstore.persist_dir)
        if stored and stored != compute_fingerprint(self.s):
            raise RuntimeError(
                "index fingerprint mismatch: config changed since the last build. "
                "Run `make build` again."
            )

    def fetched_at_for(self, url: str) -> date | None:
        """Newest fetch date for a source, used by the curated education layer."""
        dates = [c.fetched_at for c in self._chunks if c.url == url]
        if not dates:
            return None
        newest = max(dates)
        return newest.date() if hasattr(newest, "date") else date.fromisoformat(
            str(newest)[:10]
        )

    def retrieve(self, query: str, scheme: str | None = None,
                 fact_type: str | None = None) -> list[RetrievedChunk]:
        r = self.s.retrieval
        scheme_filter = scheme if r.auto_scheme_filter else None

        # Most specific first: exact scheme + fact type, then widen.
        attempts: list[dict] = []
        if scheme_filter:
            attempts.append({"scheme": scheme_filter, "fact_type": fact_type})
        if fact_type:
            attempts.append({"scheme": [scheme_filter, "_general"] if scheme_filter
                             else None, "fact_type": fact_type})
        if scheme_filter:
            attempts.append({"scheme": scheme_filter, "fact_type": None})
        if fact_type:
            attempts.append({"scheme": None, "fact_type": fact_type})
        attempts.append({"scheme": None, "fact_type": None})

        seen: set[tuple] = set()
        for spec in attempts:
            key = (str(spec["scheme"]), spec["fact_type"])
            if key in seen:
                continue
            seen.add(key)
            filters = {k: v for k, v in spec.items() if v}
            results = self._search(query, filters, r)
            if results:
                return results[:r.top_k]
        return []

    # ---- internals ----

    def _search(self, query: str, filters: dict, r) -> list[RetrievedChunk]:
        qv = self.embedder.embed_query(query)
        dense = self.store.search(qv, k=max(r.top_k * 3, 12), filters=filters)

        if not (self._bm25 and r.hybrid.enabled):
            return [d for d in dense if d.score >= r.score_threshold]

        def allow(chunk) -> bool:
            for key, want in filters.items():
                got = getattr(chunk, key)
                if isinstance(want, list):
                    if got not in want:
                        return False
                elif want and got != want:
                    return False
            return True

        keyword = self._bm25.search(query, k=max(r.top_k * 3, 12), allow=allow)
        fused = fuse(dense, keyword, r.hybrid.dense_weight, r.hybrid.bm25_weight)
        return [f for f in fused if f.score >= r.score_threshold]
