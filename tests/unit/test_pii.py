from __future__ import annotations

import pytest

from mf_facts.guardrails.pii import detect_pii, redact, verhoeff_ok


def _aadhaar_with_check_digit(prefix11: str) -> str:
    for d in "0123456789":
        candidate = prefix11 + d
        if verhoeff_ok(candidate):
            return candidate
    raise AssertionError("no check digit found")


@pytest.mark.parametrize("text,kind", [
    ("ABCDE1234F", "pan"),
    ("my pan is ABCDE1234F ok", "pan"),
    ("a@b.com", "email"),
    ("9876543210", "phone"),
    ("+919876543210", "phone"),
    ("my otp is 4321", "otp"),
    ("account no 123456789012", "account_number"),
    ("folio: 12345678901", "account_number"),
])
def test_pii_detected(text, kind):
    assert kind in {h.kind for h in detect_pii(text)}


def test_valid_aadhaar_detected():
    n = _aadhaar_with_check_digit("23456789012")
    spaced = f"{n[:4]} {n[4:8]} {n[8:]}"
    assert "aadhaar" in {h.kind for h in detect_pii(spaced)}


@pytest.mark.parametrize("text", [
    "expense ratio 0.68%",
    "exit load 1%",
    "minimum SIP 500",
    "lock-in 3 years",
    "NAV 123.4567",
    "1234567890",          # 10 digits, not a valid IN mobile (starts with 1)
])
def test_not_pii(text):
    assert detect_pii(text) == []


def test_redact_removes_value():
    out = redact("PAN ABCDE1234F and mail a@b.com")
    assert "ABCDE1234F" not in out
    assert "a@b.com" not in out
    assert "PAN_REDACTED" in out
