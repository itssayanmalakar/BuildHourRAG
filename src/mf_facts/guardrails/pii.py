"""PII detection. Runs before any logging or model call."""
from __future__ import annotations

import re
from dataclasses import dataclass

PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")
PHONE_IN = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")
PHONE_INTL = re.compile(r"(?<!\d)\+\d{10,15}(?!\d)")
OTP = re.compile(r"\b(?:otp|one[\s-]?time\s+password|verification\s+code)\b"
                 r"[^\d\n]{0,20}(\d{4,8})\b", re.I)
ACCOUNT = re.compile(r"\b(?:account|acct|folio|a/c)\b[^\d\n]{0,15}(\d{9,18})\b", re.I)
AADHAAR_RAW = re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")

_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def verhoeff_ok(number: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


@dataclass
class PIIHit:
    kind: str
    value: str
    start: int
    end: int


def _spans(text: str) -> list[PIIHit]:
    hits: list[PIIHit] = []

    for m in PAN.finditer(text):
        hits.append(PIIHit("pan", m.group(), m.start(), m.end()))
    for m in EMAIL.finditer(text):
        hits.append(PIIHit("email", m.group(), m.start(), m.end()))
    for m in OTP.finditer(text):
        hits.append(PIIHit("otp", m.group(), m.start(), m.end()))
    for m in ACCOUNT.finditer(text):
        hits.append(PIIHit("account_number", m.group(), m.start(), m.end()))
    for m in AADHAAR_RAW.finditer(text):
        digits = re.sub(r"[\s-]", "", m.group())
        if len(digits) == 12 and verhoeff_ok(digits):
            hits.append(PIIHit("aadhaar", m.group(), m.start(), m.end()))
    for m in PHONE_INTL.finditer(text):
        hits.append(PIIHit("phone", m.group(), m.start(), m.end()))
    for m in PHONE_IN.finditer(text):
        hits.append(PIIHit("phone", m.group(), m.start(), m.end()))
    return hits


def detect_pii(text: str) -> list[PIIHit]:
    """Return non-overlapping hits, preferring the longest match."""
    ordered = sorted(_spans(text), key=lambda h: (-(h.end - h.start), h.start))
    chosen: list[PIIHit] = []
    for hit in ordered:
        if all(hit.end <= c.start or hit.start >= c.end for c in chosen):
            chosen.append(hit)
    return sorted(chosen, key=lambda h: h.start)


def redact(text: str) -> str:
    for hit in reversed(detect_pii(text)):
        text = text[:hit.start] + f"[{hit.kind.upper()}_REDACTED]" + text[hit.end:]
    return text


def describe(hits: list[PIIHit]) -> str:
    return ", ".join(sorted({h.kind for h in hits}))
