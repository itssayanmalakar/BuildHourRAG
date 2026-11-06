from __future__ import annotations

import csv
from pathlib import Path

import pytest

from mf_facts.guardrails.education import (
    EDUCATION_ENTRIES,
    LOOKUP_RE,
    match_education,
)
from mf_facts.guardrails.validators import (
    ADVICE_TOKENS,
    PERF_TOKENS,
    count_sentences,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("q,key", [
    ("What is mutual funds?", "mutual_fund"),
    ("What is a mutual fund?", "mutual_fund"),
    ("What is a flexi cap fund?", "flexi_cap"),
    ("Can you give me some example of flexi cap funds?", "flexi_cap_examples"),
    ("What is SIP?", "sip"),
    ("What is a Systematic Investment Plan?", "sip"),
    ("What is NAV?", "nav"),
    ("What is ELSS?", "elss"),
    ("What is a large cap fund?", "large_cap"),
    ("What is an index fund?", "index_fund"),
    ("What is a folio?", "folio"),
    ("What is a riskometer?", "riskometer"),
    ("What is the difference between direct and regular plan?", "direct_regular"),
])
def test_match_education(q, key):
    entry = match_education(q)
    assert entry is not None
    assert entry.key == key


def test_every_entry_is_within_contract():
    for entry in EDUCATION_ENTRIES:
        assert count_sentences(entry.answer) <= 3, entry.key
        assert not ADVICE_TOKENS.search(entry.answer), entry.key
        assert not PERF_TOKENS.search(entry.answer), entry.key
        assert entry.url.startswith("https://"), entry.key
        assert LOOKUP_RE.search(f"What is {entry.key.replace('_', ' ')}?"), entry.key


def test_every_entry_citation_is_in_manifest():
    with (ROOT / "data" / "sources.csv").open(newline="", encoding="utf-8") as fh:
        urls = {row["url"].strip() for row in csv.DictReader(fh)}
    for entry in EDUCATION_ENTRIES:
        assert entry.url in urls, f"{entry.key}: {entry.url} not in data/sources.csv"


def test_education_examples_are_lookup_phrasing():
    for q in (
        "What is mutual funds?",
        "What is flexi cap?",
        "Can you give me some example of flexi cap funds?",
        "Explain ELSS",
    ):
        assert LOOKUP_RE.search(q), q
