from __future__ import annotations

from datetime import datetime, timezone

from mf_facts.chunking.atomic import detect_fact_type, split_atomic
from mf_facts.chunking.pipeline import chunk_document
from mf_facts.chunking.splitter import iter_sections, pack_paragraphs
from mf_facts.contracts import RawDoc
from mf_facts.settings import ChunkingCfg

DOC = RawDoc(
    id="demo", url="https://www.hdfcfund.com/demo", title="Demo Fund",
    amc="HDFC Mutual Fund", scheme="HDFC Flexi Cap Fund", doc_type="scheme_page",
    tier=1, fetched_at=datetime(2026, 11, 5, tzinfo=timezone.utc), http_status=200,
    extractor="trafilatura", content_hash="sha256:abc",
    text="""# HDFC Flexi Cap Fund

## Scheme facts

Expense ratio: 0.68% for the direct plan.

Exit load: 1% if redeemed within one year from the date of allotment.

## About the fund

HDFC Flexi Cap Fund is an open ended equity scheme. It invests across market
capitalisations. The scheme aims to generate long term capital appreciation by
investing in a diversified portfolio of equity and equity related instruments.

## How to download statements

You can download your capital gains statement from the AMC investor portal.
""",
)


def test_heading_sections():
    sections = list(iter_sections(DOC.text))
    names = [s for s, _ in sections]
    assert "HDFC Flexi Cap Fund > Scheme facts" in names


def test_atomic_detection():
    assert detect_fact_type("Expense ratio: 0.68%") == "expense_ratio"
    assert detect_fact_type("Exit load: 1% within one year") == "exit_load"
    assert detect_fact_type("Minimum SIP: 500") == "min_sip"
    assert detect_fact_type("Lock-in period: 3 years") == "lock_in"
    assert detect_fact_type("Benchmark: Nifty 500") == "benchmark"
    assert detect_fact_type("Hello world") is None


def test_long_paragraph_is_not_atomic():
    long_text = "Expense ratio " + ("x " * 300)
    assert split_atomic(long_text) == []


def test_chunk_document_produces_atomic_facts():
    chunks = chunk_document(DOC, ChunkingCfg())
    facts = {c.fact_type for c in chunks if c.is_atomic}
    assert {"expense_ratio", "exit_load", "statement"} <= facts
    assert all(c.url and c.scheme and c.chunk_id for c in chunks)
    assert len({c.chunk_id for c in chunks}) == len(chunks)


def test_pack_respects_size():
    paras = ["word " * 200 for _ in range(10)]
    chunks = pack_paragraphs(paras, size=200)
    assert len(chunks) > 1
