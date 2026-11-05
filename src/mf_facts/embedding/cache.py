from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np


class EmbeddingCache:
    """content_hash -> vector, so unchanged pages are never re-embedded."""

    def __init__(self, root: str, model: str, normalize: bool):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.salt = f"{model}|{normalize}"

    def _path(self, content_hash: str) -> Path:
        key = hashlib.sha256(f"{self.salt}|{content_hash}".encode()).hexdigest()
        return self.root / f"{key}.npy"

    def get(self, content_hash: str) -> list[float] | None:
        p = self._path(content_hash)
        if not p.exists():
            return None
        return np.load(p).astype(np.float32).tolist()

    def put(self, content_hash: str, vector: list[float]) -> None:
        np.save(self._path(content_hash), np.asarray(vector, dtype=np.float32))
