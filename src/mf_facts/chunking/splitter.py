"""Heading-aware splitting with paragraph packing."""
from __future__ import annotations

import re
from collections.abc import Iterator

HEADING = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def est_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))


def split_paragraphs(body: str) -> list[str]:
    parts = re.split(r"\n\s*\n", body)
    return [p.strip() for p in parts if p.strip()]


def iter_sections(markdown: str) -> Iterator[tuple[str, str]]:
    """Yield (heading_path, body). Tolerates pages with no headings."""
    stack: list[tuple[int, str]] = []
    buf: list[str] = []

    def drain() -> Iterator[tuple[str, str]]:
        body = "\n".join(buf).strip()
        if body:
            yield " > ".join(t for _, t in stack) or "Body", body

    for line in markdown.splitlines():
        m = HEADING.match(line)
        if m:
            yield from drain()
            buf.clear()
            level = len(m.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, m.group(2).strip()))
        else:
            buf.append(line)
    yield from drain()


def _split_oversized(para: str, size: int) -> list[str]:
    sentences = [s for s in SENT_SPLIT.split(para) if s.strip()]
    out, cur = [], []
    for s in sentences:
        if cur and est_tokens(" ".join(cur + [s])) > size:
            out.append(" ".join(cur))
            cur = []
        cur.append(s)
    if cur:
        out.append(" ".join(cur))
    return out


def pack_paragraphs(paragraphs: list[str], size: int = 700) -> list[str]:
    """Greedily pack paragraphs up to ~size tokens, splitting oversized ones."""
    chunks: list[str] = []
    cur: list[str] = []

    def flush() -> None:
        nonlocal cur
        if cur:
            chunks.append("\n\n".join(cur))
            cur = []

    for para in paragraphs:
        if est_tokens(para) > size:
            flush()
            chunks.extend(_split_oversized(para, size))
            continue
        if cur and est_tokens("\n\n".join(cur + [para])) > size:
            flush()
        cur.append(para)
    flush()
    return chunks
