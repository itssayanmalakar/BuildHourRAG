from __future__ import annotations

from mf_facts.embedding.pipeline import build_embedder
from mf_facts.vectorstore.chroma_store import ChromaStore


def build_vectorstore(settings):
    cfg = settings.phases.vectorstore
    if cfg.backend == "chroma":
        return ChromaStore(cfg.persist_dir, cfg.collection)
    raise NotImplementedError(
        f"vector backend {cfg.backend!r} is not wired; add an adapter in "
        f"src/mf_facts/vectorstore/ and register it here"
    )


def build_llm(settings):
    cfg = settings.llm
    if cfg.provider == "groq":
        from mf_facts.llm.groq_client import GroqLLM

        return GroqLLM(
            api_key=settings.llm_api_key,
            model=settings.llm_model or "",
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            timeout_s=cfg.timeout_s,
            max_retries=cfg.max_retries,
        )
    raise NotImplementedError(f"llm provider {cfg.provider!r} is not wired")
