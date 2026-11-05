"""Detect fact lines that must never be split from their labels."""
from __future__ import annotations

import re

FACT_PATTERNS: dict[str, re.Pattern] = {
    "expense_ratio": re.compile(
        r"(total expense ratio|\bexpense ratio\b|\bTER\b)", re.I),
    "exit_load": re.compile(r"\bexit load\b", re.I),
    "min_sip": re.compile(
        r"(minimum\s+(sip|investment|application|additional purchase|purchase)"
        r"|\bmin\.?\s*sip\b)", re.I),
    "lock_in": re.compile(r"\block[\s-]?in\b", re.I),
    "riskometer": re.compile(r"(risk[\s-]?o[\s-]?meter|riskometer)", re.I),
    "benchmark": re.compile(r"\bbenchmark\b", re.I),
    "statement": re.compile(
        r"(capital\s*gains?\s+statement|account statement|"
        r"download\s+(?:your\s+)?(?:capital\s*gains?|account)?\s*statement)", re.I),
    "scheme_meta": re.compile(
        r"(\bfund category\b|\bplan\b|\bdirect plan\b|\bregular plan\b|"
        r"\bfund manager\b|\baum\b|\bnav\b)", re.I),
}

MAX_ATOMIC_CHARS = 420


def detect_fact_type(text: str) -> str | None:
    for fact, pat in FACT_PATTERNS.items():
        if pat.search(text):
            return fact
    return None


def split_atomic(paragraph: str) -> list[tuple[str, str]]:
    """Return [(paragraph, fact_type)] when the paragraph is a self-contained fact."""
    p = paragraph.strip()
    if not p or len(p) > MAX_ATOMIC_CHARS:
        return []
    fact = detect_fact_type(p)
    return [(p, fact)] if fact else []
