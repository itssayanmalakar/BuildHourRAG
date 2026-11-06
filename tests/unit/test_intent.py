from __future__ import annotations

import pytest

from mf_facts.guardrails.intent import Intent, detect_scheme, route

SCHEMES = [
    "HDFC Flexi Cap Fund",
    "HDFC Large Cap Fund",
    "HDFC ELSS Tax Saver Fund",
    "HDFC Nifty 50 Index Fund",
]


@pytest.mark.parametrize("q,intent", [
    ("What is the expense ratio of HDFC Flexi Cap Fund?", Intent.EXPENSE_RATIO),
    ("Exit load if I redeem in 6 months?", Intent.EXIT_LOAD),
    ("Minimum SIP amount?", Intent.MIN_SIP),
    ("Lock-in for ELSS?", Intent.LOCK_IN),
    ("Riskometer level?", Intent.RISKOMETER),
    ("Benchmark of HDFC Index Fund?", Intent.BENCHMARK),
    ("How do I download my capital gains statement?", Intent.STATEMENT),
    ("What is the fund category?", Intent.SCHEME_META),
])
def test_fact_intents(q, intent):
    assert route(q, SCHEMES) == intent


@pytest.mark.parametrize("q,intent", [
    ("Should I buy HDFC Flexi Cap Fund?", Intent.ADVICE),
    ("Which fund is best for me?", Intent.ADVICE),
    ("Which fund gave the best 3-year returns?", Intent.PERFORMANCE),
    ("What CAGR can I expect?", Intent.PERFORMANCE),
    ("How much should I allocate to ELSS?", Intent.PORTFOLIO),
    ("Will NAV go up next month?", Intent.PREDICTION),
    ("What is the expense ratio of SBI Bluechip Fund?", Intent.OUT_OF_SCOPE),
])
def test_refusal_intents(q, intent):
    assert route(q, SCHEMES) == intent


def test_exit_load_sell_is_not_advice():
    assert route("Exit load if I sell my units?", SCHEMES) == Intent.EXIT_LOAD


@pytest.mark.parametrize("q,intent", [
    ("What is a mutual fund?", Intent.EDUCATION),
    ("What is mutual funds?", Intent.EDUCATION),
    ("What is a flexi cap fund?", Intent.EDUCATION),
    ("Can you give me some example of flexi cap funds?", Intent.EDUCATION),
    ("What is SIP?", Intent.EDUCATION),
    ("What is NAV?", Intent.EDUCATION),
    ("What is a riskometer?", Intent.EDUCATION),
    ("What is the difference between direct and regular plan?", Intent.EDUCATION),
    ("What is the expense ratio?", Intent.EDUCATION),
])
def test_education_intents(q, intent):
    assert route(q, SCHEMES) == intent


def test_scheme_fact_beats_education():
    assert route("What is the expense ratio of HDFC Flexi Cap Fund?", SCHEMES) == \
        Intent.EXPENSE_RATIO


def test_refusal_beats_education():
    assert route("Should I buy a flexi cap fund?", SCHEMES) == Intent.ADVICE
    assert route("What is the best flexi cap fund?", SCHEMES) == Intent.ADVICE


def test_statement_download_stays_on_fact_path():
    assert route("How do I download my capital gains statement?", SCHEMES) == \
        Intent.STATEMENT


def test_scheme_detection_full_name():
    assert detect_scheme("expense ratio of hdfc elss tax saver fund", SCHEMES) == \
        "HDFC ELSS Tax Saver Fund"


def test_scheme_detection_alias():
    assert detect_scheme("lock-in for elss?", SCHEMES) == "HDFC ELSS Tax Saver Fund"


def test_scheme_detection_nifty():
    assert detect_scheme("benchmark of nifty 50 index fund", SCHEMES) == \
        "HDFC Nifty 50 Index Fund"


def test_scheme_detection_large_cap():
    assert detect_scheme("expense ratio of large cap fund", SCHEMES) == \
        "HDFC Large Cap Fund"


def test_scheme_detection_none():
    assert detect_scheme("minimum sip amount?", SCHEMES) is None
