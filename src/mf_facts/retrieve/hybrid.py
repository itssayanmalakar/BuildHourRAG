"""BM25 keyword retrieval and weighted fusion with dense scores."""
from __future__ import annotations

import re

from mf_facts.contracts import Chunk, RetrievedChunk

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class BM25Index:
    def __init__(self, chunks: list[Chunk]):
        from rank_bm25 import BM25Okapi

        self.chunks = chunks
        if not chunks:
            self.bm25 = None
            return
        self.bm25 = BM25Okapi([tokenize(c.text) or ["_"] for c in chunks])

    def search(self, query: str, k: int = 10,
               allow=None) -> list[RetrievedChunk]:
        if self.bm25 is None:
            return []
        scores = self.bm25.get_scores(tokenize(query))
        idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        idx = [i for i in idx if scores[i] > 0 and (allow is None or allow(self.chunks[i]))][:k]
        if not idx:
            return []
        hi = max(scores[i] for i in idx) or 1.0
        return [
            RetrievedChunk(chunk=self.chunks[i], score=float(scores[i] / hi), source="bm25")
            for i in idx
        ]


def fuse(dense: list[RetrievedChunk], keyword: list[RetrievedChunk],
         dense_weight: float, bm25_weight: float, k: int = 60) -> list[RetrievedChunk]:
    """Reciprocal-rank fusion: robust when dense and BM25 scores use different scales."""
    table: dict[str, RetrievedChunk] = {}
    scores: dict[str, float] = {}
    for weight, items in ((dense_weight, dense), (bm25_weight, keyword)):
        for rank, r in enumerate(items, 1):
            cid = r.chunk.chunk_id
            scores[cid] = scores.get(cid, 0.0) + weight / (k + rank)
            if cid not in table:
                table[cid] = RetrievedChunk(chunk=r.chunk, score=0.0, source="fused")

    if not scores:
        return []
    top = max(scores.values())
    for cid, score in scores.items():
        table[cid].score = score / top  # normalise to 1.0 for the score threshold
    return sorted(table.values(), key=lambda r: r.score, reverse=True)
