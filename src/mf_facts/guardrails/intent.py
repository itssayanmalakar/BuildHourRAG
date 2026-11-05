"""Deterministic, pre-LLM intent routing. Refusals never depend on the model."""
from __future__ import annotations

import re
from enum import Enum


class Intent(str, Enum):
    EXPENSE_RATIO = "expense_ratio"
    EXIT_LOAD = "exit_load"
    MIN_SIP = "min_sip"
    LOCK_IN = "lock_in"
    RISKOMETER = "riskometer"
    BENCHMARK = "benchmark"
    STATEMENT = "statement"
    SCHEME_META = "scheme_meta"
    ADVICE = "advice"
    PERFORMANCE = "performance"
    PORTFOLIO = "portfolio"
    PREDICTION = "prediction"
    OUT_OF_SCOPE = "out_of_scope"
    UNKNOWN = "unknown"


REFUSAL = {Intent.ADVICE, Intent.PERFORMANCE, Intent.PORTFOLIO, Intent.PREDICTION}
FACT = {
    Intent.EXPENSE_RATIO, Intent.EXIT_LOAD, Intent.MIN_SIP, Intent.LOCK_IN,
    Intent.RISKOMETER, Intent.BENCHMARK, Intent.STATEMENT, Intent.SCHEME_META,
}

ADVICE_RE = re.compile(
    r"\b(should i|shall i|is it (good|safe|worth)|worth investing|is this fund good"
    r"|recommend|recommendation|advice|suggest|which fund is best|best fund"
    r"|better fund|better than|which (one )?is better|compare|comparison|versus"
    r"|invest or not)\b", re.I)
PERFORMANCE_RE = re.compile(
    r"\b(returns?|cagr|xirr|annualis|annualiz|outperform|underperform"
    r"|multibagger|how much (will|would) i (get|earn)|past performance)\b", re.I)
PORTFOLIO_RE = re.compile(
    r"\b(portfolio|allocation|allocate|rebalanc|diversif|how much (to|should) invest"
    r"|asset allocation|split my (money|investment))\b", re.I)
PREDICTION_RE = re.compile(
    r"\b(will (it|nav|the fund|this fund|market) (go up|rise|fall|crash|grow)"
    r"|predict|forecast|next (month|year))\b", re.I)

OTHER_AMC_RE = re.compile(
    r"\b(icici|sbi|axis|kotak|aditya birla|nippon|franklin|dsp|tata|uti|mirae"
    r"|parag parikh|quant|motilal|edelweiss|bandhan|navi|zerodha|hsbc|invesco"
    r"|canara|lic|shriram|whiteoak)\b", re.I)

FACT_RULES: list[tuple[Intent, re.Pattern]] = [
    (Intent.EXPENSE_RATIO, re.compile(r"(expense ratio|total expense|\bter\b)", re.I)),
    (Intent.EXIT_LOAD, re.compile(r"exit load", re.I)),
    (Intent.MIN_SIP, re.compile(
        r"(minimum\s+(sip|investment|application|additional|purchase)|\bmin\.?\s*sip\b"
        r"|sip amount)", re.I)),
    (Intent.LOCK_IN, re.compile(r"lock[\s-]?in", re.I)),
    (Intent.RISKOMETER, re.compile(
        r"(risk[\s-]?o[\s-]?meter|riskometer|risk (level|grade|profile))", re.I)),
    (Intent.BENCHMARK, re.compile(r"\bbenchmark\b", re.I)),
    (Intent.STATEMENT, re.compile(
        r"(statement|capital\s*gains|download.*(report|statement))", re.I)),
    (Intent.SCHEME_META, re.compile(
        r"(fund category|category of the fund|\bplan\b|direct plan|regular plan"
        r"|fund manager|\baum\b|\bnav\b|scheme information)", re.I)),
]


def route(question: str, scope_schemes: list[str]) -> Intent:
    q = question.strip()
    if not q:
        return Intent.UNKNOWN

    if PERFORMANCE_RE.search(q):
        return Intent.PERFORMANCE
    if PREDICTION_RE.search(q):
        return Intent.PREDICTION
    if PORTFOLIO_RE.search(q):
        return Intent.PORTFOLIO
    if ADVICE_RE.search(q):
        return Intent.ADVICE

    in_scope = any(s.lower() in q.lower() for s in scope_schemes)
    if OTHER_AMC_RE.search(q) and not in_scope:
        return Intent.OUT_OF_SCOPE

    for intent, pattern in FACT_RULES:
        if pattern.search(q):
            return intent
    return Intent.UNKNOWN


def detect_scheme(question: str, scope_schemes: list[str]) -> str | None:
    q = question.lower()
    for scheme in scope_schemes:
        if scheme.lower() in q:
            return scheme

    # aliases: the distinctive words in each configured scheme name
    distinctive = {"elss", "flexi", "nifty", "index", "large", "saver"}
    best: tuple[int, str] | None = None
    for scheme in scope_schemes:
        tokens = [t for t in re.split(r"[\s-]+", scheme.lower())
                  if t not in {"hdfc", "fund", "plan", "the", "tax"} and len(t) > 3]
        hits = sum(t in q for t in tokens)
        if hits and any(t in distinctive and t in q for t in tokens):
            if best is None or hits > best[0]:
                best = (hits, scheme)
    return best[1] if best else None
