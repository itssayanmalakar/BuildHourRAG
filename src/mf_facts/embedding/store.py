"""Phase 3 + 4 bridge: load cached vectors and upsert them into the vector DB."""
from __future__ import annotations

import json
from pathlib import Path

from mf_facts.embedding.cache import EmbeddingCache
from mf_facts.embedding.pipeline import build_embedder, load_chunks
from mf_facts.vectorstore.fingerprint import compute_fingerprint, write_fingerprint


def run_index(settings) -> dict:
    from mf_facts.registry import build_vectorstore

    cfg = settings.phases.vectorstore
    ecfg = settings.phases.embedding
    chunks = load_chunks(settings)
    embedder = build_embedder(settings)

    cache = EmbeddingCache(ecfg.cache_dir, ecfg.model, ecfg.normalize)
    vectors: list[list[float]] = []
    missing: list[str] = []
    for c in chunks:
        v = cache.get(c.content_hash)
        if v is None:
            missing.append(c.chunk_id)
        else:
            vectors.append(v)

    if missing:
        raise RuntimeError(
            f"{len(missing)} chunks are not embedded — run `mf-facts embed` first "
            f"(e.g. {missing[:3]})"
        )

    store = build_vectorstore(settings)
    store.ensure_collection(embedder.dim, cfg.distance, reset=cfg.reset_on_rebuild)
    store.upsert(chunks, vectors)

    fp = compute_fingerprint(settings)
    write_fingerprint(cfg.persist_dir, fp)
    Path(cfg.persist_dir, "config.snapshot.yaml").write_text(
        Path("config.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (Path(cfg.persist_dir) / "index_meta.json").write_text(
        json.dumps({"chunks": len(chunks), "dim": embedder.dim,
                    "model": ecfg.model, "fingerprint": fp}, indent=2),
        encoding="utf-8",
    )

    return {"indexed": store.count(), "dim": embedder.dim,
            "fingerprint": fp[:16], "backend": cfg.backend}
