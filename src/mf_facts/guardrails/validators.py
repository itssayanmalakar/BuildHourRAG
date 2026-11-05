"""Fail-closed output checks. Pure functions so they are easy to test."""
from __future__ import annotations

import re

ADVICE_TOKENS = re.compile(
    r"\b(you should|i recommend|we recommend|i suggest|better to|must buy|sell now"
    r"|guaranteed|sure shot|risk[- ]free|assured returns)\b", re.I)

PERF_TOKENS = re.compile(
    r"\b(cagr|annualised|annualized|xirr|outperform|underperform|alpha|beta)\b"
    r"|\b\d+(\.\d+)?\s?%\s*(return|returns|p\.a\.|per annum)", re.I)

SOURCE_LINE = re.compile(r"^Source:\s*(\S+)\s*$", re.M)
STAMP = re.compile(r"^Last updated from sources:\s*\d{4}-\d{2}-\d{2}\s*$", re.M)

_ABBREV = {"rs.": "Rs<DOT>", "e.g.": "e<DOT>g<DOT>", "i.e.": "i<DOT>e<DOT>"}


def _protect(text: str) -> str:
    for abbr, repl in _ABBREV.items():
        text = text.replace(abbr, repl)
    return text


def _restore(text: str) -> str:
    for abbr, repl in _ABBREV.items():
        text = text.replace(repl, abbr)
    return text


def count_sentences(text: str) -> int:
    t = _protect(text.strip())
    parts = [p for p in re.split(r"(?<=[.!?])\s+", t) if p.strip()]
    return len(parts) if parts else 0


def truncate_sentences(text: str, limit: int) -> str:
    if count_sentences(text) <= limit:
        return text
    parts = re.split(r"(?<=[.!?])\s+", _protect(text.strip()))
    return _restore(" ".join(parts[:limit]).strip())


def issues(composed: str, citation_url: str | None, is_citable,
           max_sentences: int = 3) -> list[str]:
    problems: list[str] = []
    if citation_url and not is_citable(citation_url):
        problems.append("citation_not_in_manifest")
    if not SOURCE_LINE.search(composed):
        problems.append("missing_source_line")
    if not STAMP.search(composed):
        problems.append("missing_date_stamp")
    body = STAMP.sub("", SOURCE_LINE.sub("", composed))
    if count_sentences(body) > max_sentences:
        problems.append("too_many_sentences")
    if ADVICE_TOKENS.search(body):
        problems.append("advice_tokens")
    if PERF_TOKENS.search(body):
        problems.append("performance_tokens")
    return problems


def is_valid(composed: str, citation_url: str | None, is_citable,
             max_sentences: int = 3) -> bool:
    return not issues(composed, citation_url, is_citable, max_sentences)
