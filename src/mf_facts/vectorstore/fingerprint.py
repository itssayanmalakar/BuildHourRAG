"""Index fingerprint: makes 'retrieval uses the ingestion backend' enforceable."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def compute_fingerprint(settings) -> str:
    payload = {
        "embedding": [
            settings.phases.embedding.provider,
            settings.phases.embedding.model,
            settings.phases.embedding.normalize,
        ],
        "chunking": [
            settings.phases.chunking.strategy,
            settings.phases.chunking.chunk_size,
            settings.phases.chunking.chunk_overlap,
            settings.phases.chunking.atomic_fact_chunks,
        ],
        "store": [
            settings.phases.vectorstore.backend,
            settings.phases.vectorstore.distance,
        ],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def write_fingerprint(index_dir: str, fp: str) -> None:
    Path(index_dir).mkdir(parents=True, exist_ok=True)
    (Path(index_dir) / "fingerprint.txt").write_text(fp, encoding="utf-8")


def read_fingerprint(index_dir: str) -> str | None:
    p = Path(index_dir) / "fingerprint.txt"
    return p.read_text(encoding="utf-8").strip() if p.exists() else None
