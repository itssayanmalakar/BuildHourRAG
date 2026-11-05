"""Single source of truth for configuration. Nothing else reads config.yaml."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator


class AppCfg(BaseModel):
    name: str = "MF Facts Bot"
    disclaimer: str = "Facts-only. No investment advice."
    max_answer_sentences: int = 3
    require_citation: bool = True
    ui: Literal["streamlit", "fastapi"] = "streamlit"


class ScopeCfg(BaseModel):
    amc: str
    schemes: list[str]
    sources_manifest: str = "data/sources.csv"
    allowlist_domains: list[str]

    @model_validator(mode="after")
    def _check(self) -> "ScopeCfg":
        if not 1 <= len(self.schemes) <= 8:
            raise ValueError("scope.schemes must contain 1-8 schemes")
        if not self.allowlist_domains:
            raise ValueError("scope.allowlist_domains must not be empty")
        return self


class LoadingCfg(BaseModel):
    fetcher: Literal["jina", "curl_cffi", "httpx", "playwright"] = "jina"
    respect_robots_txt: bool = True
    request_delay_ms: int = 1200
    timeout_s: int = 40
    retries: int = 3
    extractor: Literal["trafilatura", "bs4"] = "trafilatura"
    needs_js_fallback: bool = False
    cache_dir: str = "data/raw"


class ChunkingCfg(BaseModel):
    strategy: Literal["heading_aware", "recursive"] = "heading_aware"
    chunk_size: int = 700
    chunk_overlap: int = 120
    min_chunk_chars: int = 120
    atomic_fact_chunks: bool = True
    dedupe: bool = True
    output: str = "data/chunks.jsonl"


class EmbeddingCfg(BaseModel):
    provider: Literal["local", "openai", "gemini", "cohere", "mistral"] = "local"
    model: str = "BAAI/bge-small-en-v1.5"
    batch_size: int = 32
    normalize: bool = True
    cache: bool = True
    cache_dir: str = "data/embed_cache"


class VectorStoreCfg(BaseModel):
    backend: Literal["chroma", "faiss", "qdrant", "pgvector"] = "chroma"
    collection: str = "mf_facts"
    persist_dir: str = "data/index"
    distance: Literal["cosine", "l2", "ip"] = "cosine"
    reset_on_rebuild: bool = True


class HybridCfg(BaseModel):
    enabled: bool = True
    dense_weight: float = 0.65
    bm25_weight: float = 0.35


class RerankCfg(BaseModel):
    enabled: bool = False
    model: str = "BAAI/bge-reranker-base"


class RetrievalCfg(BaseModel):
    use_same_backend_as_ingestion: bool = True
    top_k: int = 6
    score_threshold: float = 0.25
    auto_scheme_filter: bool = True
    hybrid: HybridCfg = Field(default_factory=HybridCfg)
    rerank: RerankCfg = Field(default_factory=RerankCfg)


class LLMCfg(BaseModel):
    provider: Literal["groq", "gemini", "openai", "anthropic", "mistral"] = "groq"
    model_env: str = "GROQ_MODEL"
    temperature: float = 0.0
    max_tokens: int = 350
    timeout_s: int = 20
    max_retries: int = 1
    fallback_provider: str | None = None


class GuardrailsCfg(BaseModel):
    refuse_advice: bool = True
    block_performance_claims: bool = True
    block_pii: bool = True
    pii_types: list[str] = Field(
        default_factory=lambda: [
            "pan", "aadhaar", "account_number", "otp", "email", "phone",
        ]
    )
    max_sentences: int = 3
    citation_must_be_in_corpus: bool = True
    log_raw_pii: bool = False


class LoggingCfg(BaseModel):
    level: str = "INFO"
    redact_pii: bool = True
    trace_dir: str = "data/traces"


class PhasesCfg(BaseModel):
    loading: LoadingCfg = Field(default_factory=LoadingCfg)
    chunking: ChunkingCfg = Field(default_factory=ChunkingCfg)
    embedding: EmbeddingCfg = Field(default_factory=EmbeddingCfg)
    vectorstore: VectorStoreCfg = Field(default_factory=VectorStoreCfg)


class Settings(BaseModel):
    app: AppCfg
    scope: ScopeCfg
    phases: PhasesCfg
    retrieval: RetrievalCfg = Field(default_factory=RetrievalCfg)
    llm: LLMCfg = Field(default_factory=LLMCfg)
    guardrails: GuardrailsCfg = Field(default_factory=GuardrailsCfg)
    logging: LoggingCfg = Field(default_factory=LoggingCfg)

    @classmethod
    def load(cls, path: str | Path = "config.yaml") -> "Settings":
        load_dotenv(override=False)
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(raw)

    # ---- secrets are resolved from the environment, never from config.yaml ----

    @property
    def llm_api_key(self) -> str | None:
        return os.getenv(f"{self.llm.provider.upper()}_API_KEY")

    @property
    def llm_model(self) -> str | None:
        return os.getenv(self.llm.model_env)

    def validate_runtime(self) -> None:
        missing = [
            name
            for name, value in (
                (f"{self.llm.provider.upper()}_API_KEY", self.llm_api_key),
                (self.llm.model_env, self.llm_model),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing from .env: " + ", ".join(missing)
                + ". Copy .env.example to .env and fill it in."
            )


def get_settings(path: str | Path = "config.yaml") -> Settings:
    return Settings.load(path)
