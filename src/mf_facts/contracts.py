"""Typed records that flow between pipeline stages."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

FactType = Literal[
    "expense_ratio", "exit_load", "min_sip", "lock_in",
    "riskometer", "benchmark", "statement", "scheme_meta",
]
DocType = Literal[
    "scheme_page", "factsheet", "ter_page", "help_page",
    "screener", "blog", "regulator",
]
AnswerKind = Literal["answer", "refusal", "not_found", "pii_rejected"]


class SourceSpec(BaseModel):
    id: str
    url: str
    title: str
    tier: int
    amc: str
    scheme: str
    doc_type: DocType
    enabled: bool = True
    needs_js: bool = False


class RawDoc(BaseModel):
    id: str
    url: str
    title: str
    amc: str
    scheme: str
    doc_type: DocType
    tier: int
    fetched_at: datetime
    http_status: int
    extractor: str
    text: str
    content_hash: str
    warnings: list[str] = Field(default_factory=list)


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    url: str
    title: str
    amc: str
    scheme: str
    doc_type: DocType
    section: str
    fact_type: FactType | None = None
    is_atomic: bool = False
    text: str
    token_count: int
    fetched_at: datetime
    content_hash: str


class RetrievedChunk(BaseModel):
    chunk: Chunk
    score: float
    source: Literal["dense", "bm25", "fused"] = "fused"


class Answer(BaseModel):
    kind: AnswerKind
    text: str
    citation_url: str | None = None
    updated_at: date | None = None
    scheme: str | None = None
    trace_id: str = ""

    def card(self) -> str:
        lines = [self.text.strip()]
        if self.citation_url:
            lines.append(f"Source: {self.citation_url}")
        if self.updated_at:
            lines.append(f"Last updated from sources: {self.updated_at.isoformat()}")
        return "\n".join(lines)
