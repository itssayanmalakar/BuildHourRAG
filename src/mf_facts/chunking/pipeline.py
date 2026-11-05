"""Phase 2 driver: data/raw/*.json -> data/chunks.jsonl."""
from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from pathlib import Path

from mf_facts.chunking.atomic import detect_fact_type, split_atomic
from mf_facts.chunking.splitter import (
    est_tokens,
    iter_sections,
    pack_paragraphs,
    split_paragraphs,
)
from mf_facts.contracts import Chunk, RawDoc

log = logging.getLogger(__name__)

PERF_SECTION = re.compile(
    r"(historical performance|benchmark performance|trailing returns|"
    r"performance overview|scheme performance)",
    re.I,
)


def _emit(doc: RawDoc, section: str, text: str, fact: str | None,
          atomic: bool, n: int) -> Chunk:
    slug = fact or "body"
    return Chunk(
        chunk_id=f"{doc.id}#{slug}#{n}",
        doc_id=doc.id, url=doc.url, title=doc.title, amc=doc.amc,
        scheme=doc.scheme, doc_type=doc.doc_type, section=section,
        fact_type=fact, is_atomic=atomic, text=text,
        token_count=est_tokens(text), fetched_at=doc.fetched_at,
        content_hash=doc.content_hash,
    )


def chunk_document(doc: RawDoc, cfg) -> list[Chunk]:
    out: list[Chunk] = []
    counter: Counter[str] = Counter()

    for section, body in iter_sections(doc.text):
        if PERF_SECTION.search(section):
            # performance tables are out of scope by design
            continue
        section_fact = detect_fact_type(section)
        atomic: list[tuple[str, str]] = []
        rest: list[str] = []

        for para in split_paragraphs(body):
            hits = split_atomic(para) if cfg.atomic_fact_chunks else []
            if hits:
                atomic.extend(hits)
            else:
                rest.append(para)

        for text, fact in atomic:
            counter[fact] += 1
            out.append(_emit(doc, section, text, fact, True, counter[fact]))

        for text in pack_paragraphs(rest, cfg.chunk_size):
            if len(text) < cfg.min_chunk_chars:
                continue
            slug = section_fact or "body"
            counter[slug] += 1
            out.append(_emit(doc, section, text, section_fact, False, counter[slug]))

    if cfg.dedupe:
        seen: set[str] = set()
        unique: list[Chunk] = []
        for c in out:
            key = hashlib.sha256(c.text.lower().encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                unique.append(c)
        out = unique

    # keep chunk ids unique after dedupe
    by_id: set[str] = set()
    for c in out:
        base, i = c.chunk_id, 2
        while c.chunk_id in by_id:
            c.chunk_id = f"{base}~{i}"
            i += 1
        by_id.add(c.chunk_id)
    return out


def run_chunk(settings) -> dict:
    cfg = settings.phases.chunking
    out_path = Path(cfg.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    docs = 0
    total = 0
    atomic = 0
    facts: Counter[str] = Counter()

    with out_path.open("w", encoding="utf-8") as fh:
        for path in sorted(Path(settings.phases.loading.cache_dir).glob("*.json")):
            doc = RawDoc.model_validate_json(path.read_text(encoding="utf-8"))
            chunks = chunk_document(doc, cfg)
            docs += 1
            for c in chunks:
                fh.write(c.model_dump_json() + "\n")
                total += 1
                atomic += int(c.is_atomic)
                if c.fact_type:
                    facts[c.fact_type] += 1

    return {
        "documents": docs,
        "chunks": total,
        "atomic": atomic,
        "fact_types": dict(facts.most_common()),
        "output": str(out_path),
    }
