from __future__ import annotations

from mf_facts.guardrails.validators import (
    count_sentences,
    issues,
    truncate_sentences,
)


def test_decimals_are_not_sentence_breaks():
    assert count_sentences("Expense ratio is 0.68%. Exit load is 1%.") == 2


def test_truncate_to_three():
    assert truncate_sentences("A. B. C. D.", 3) == "A. B. C."


def test_counts_plain_sentence():
    assert count_sentences("The lock-in period is three years.") == 1


def test_fake_citation_rejected():
    composed = (
        "The expense ratio is 0.68%.\n"
        "Source: https://evil.example/fund\n"
        "Last updated from sources: 2026-11-05"
    )
    problems = issues(composed, "https://evil.example/fund",
                      is_citable=lambda u: False, max_sentences=3)
    assert "citation_not_in_manifest" in problems


def test_valid_card_passes():
    composed = (
        "The exit load is 1% within one year.\n"
        "Source: https://www.hdfcfund.com/x\n"
        "Last updated from sources: 2026-11-05"
    )
    assert issues(composed, "https://www.hdfcfund.com/x",
                  is_citable=lambda u: True, max_sentences=3) == []


def test_advice_tokens_flagged():
    composed = (
        "You should buy this fund now.\n"
        "Source: https://www.hdfcfund.com/x\n"
        "Last updated from sources: 2026-11-05"
    )
    assert "advice_tokens" in issues(composed, "https://www.hdfcfund.com/x",
                                     is_citable=lambda u: True)


def test_performance_tokens_flagged():
    composed = (
        "This fund gave 18% returns last year.\n"
        "Source: https://www.hdfcfund.com/x\n"
        "Last updated from sources: 2026-11-05"
    )
    assert "performance_tokens" in issues(composed, "https://www.hdfcfund.com/x",
                                          is_citable=lambda u: True)
