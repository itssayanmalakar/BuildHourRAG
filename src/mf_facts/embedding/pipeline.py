from __future__ import annotations

import logging
from pathlib import Path

from mf_facts.contracts import Chunk
from mf_facts.embedding.base import Embedder
from mf_facts.embedding.cache import EmbeddingCache
from mf_facts.embedding.local_st import LocalEmbedder

log = logging.getLogger(__name__)


def build_embedder(settings) -> Embedder:
    cfg = settings.phases.embedding
    if cfg.provider == "local":
        return LocalEmbedder(cfg.model, cfg.normalize, cfg.batch_size)
    raise NotImplementedError(
        f"embedding provider {cfg.provider!r} is not wired; add an adapter in "
        f"src/mf_facts/embedding/ and register it here"
    )


def load_chunks(settings) -> list[Chunk]:
    path = Path(settings.phases.chunking.output)
    if not path.exists():
        raise RuntimeError(f"{path} missing — run `mf-facts chunk` first")
    return [Chunk.model_validate_json(line)
            for line in path.open(encoding="utf-8") if line.strip()]


def run_embed(settings) -> dict:
    cfg = settings.phases.embedding
    chunks = load_chunks(settings)
    embedder = build_embedder(settings)
    cache = EmbeddingCache(cfg.cache_dir, cfg.model, cfg.normalize) if cfg.cache else None

    pending: list[Chunk] = []
    hits = 0
    for c in chunks:
        if cache and cache.get(c.content_hash) is not None:
            hits += 1
        else:
            pending.append(c)

    for i in range(0, len(pending), cfg.batch_size):
        batch = pending[i:i + cfg.batch_size]
        vectors = embedder.embed_documents([c.text for c in batch])
        for c, v in zip(batch, vectors):
            if cache:
                cache.put(c.content_hash, v)
        log.info("embedded %d/%d", min(i + cfg.batch_size, len(pending)), len(pending))

    return {
        "chunks": len(chunks),
        "cache_hits": hits,
        "embedded": len(pending),
        "dim": embedder.dim,
        "model": cfg.model,
    }
