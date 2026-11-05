"""HTML -> clean markdown-ish text, preserving headings and tables."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

_WS = re.compile(r"[ \t\xa0]+")
_NL = re.compile(r"\n{3,}")
_SENT_PAD = re.compile(r"(?<=[.!?])(?=[A-Z])")
# performance tickers injected by the AMC site chrome, e.g. "HDFC Flexi Cap Fund 5Y : 15.67%"
_TICKER = re.compile(r"\b\d+\s*Y\s*:\s*\d+(?:\.\d+)?\s*%")
_MAX_PCT_LINE = re.compile(r"^\s*(?:[-*]\s*)?(?:1Y|3Y|5Y|10Y|YTD|Since inception)\b", re.I)
_PERF_LINE = re.compile(
    r"(scheme returns|benchmark returns|additional benchmark returns?|value of investment"
    r"|past performance|trailing returns|annualised returns|annualized returns"
    r"|\bcagr\b|absolute returns|returns? since inception|benchmark\s*\(rs)",
    re.I,
)
_PURE_PCT = re.compile(r"^\s*\|?\s*\d+(?:\.\d+)?\s*%\s*\|?\s*$")
_PURE_RETURNS = re.compile(r"^\s*\|?\s*(?:scheme|benchmark|additional\s+benchmark)?\s*returns?\s*\|?\s*$", re.I)

_LABEL_HEADING = re.compile(r"^#{1,4}\s*(.+?)\s*$")
_VALUE_LABELS = {
    "ter", "expense ratio", "min sip", "minimum sip", "lock in", "lock-in",
    "riskometer", "benchmark", "entry load", "exit load", "nav", "aum",
}
_LABEL_CANON = {
    "ter": "Total expense ratio (TER)",
    "expense ratio": "Total expense ratio (TER)",
    "min sip": "Minimum SIP amount",
    "minimum sip": "Minimum SIP amount",
    "lock in": "Lock-in period",
    "lock-in": "Lock-in period",
    "riskometer": "Riskometer level",
    "benchmark": "Benchmark index",
    "exit load": "Exit load",
    "entry load": "Entry load",
}

_UI_LINES = {
    "#", "##", "###", "####", "OR", "PAN", "Folio", "Send OTP", "Duration",
    "Current Financial Year", "SEND EMAIL", "Ask Me", "INVEST NOW", "KNOW MORE",
    "DIRECT", "REGULAR", "SORT", "All Funds", "Spotlight Funds", "Equity",
    "Debt", "Hybrid", "Solution Oriented", "Font Size", "Mode Switcher",
    "Text Magnifier", "Reading Line", "Invest / Login", "Trending Searches",
    "Skip to Content",
}


def strip_ui_noise(text: str) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s in _UI_LINES:
            continue
        if re.fullmatch(r"#{1,6}", s):
            continue
        if s.lower() in {"invest / login", "trending searches", "skip to content"}:
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def join_label_values(text: str) -> str:
    """Turn `### TER` + `0.75` into `TER: 0.75` so the fact survives chunking."""
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = _LABEL_HEADING.match(line.strip())
        label = m.group(1).strip() if m else line.strip()
        if label.lower() in _VALUE_LABELS:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                val = lines[j].strip()
                skip = j - i
                if val.endswith("...") and j + 1 < len(lines):
                    nxt = lines[j + 1].strip()
                    if nxt and not nxt.startswith("#") and len(nxt) <= 120:
                        val = nxt
                        skip = j + 1 - i
                already = re.match(rf"^{re.escape(label)}\s*:\s*", val, re.I)
                if val and not val.startswith("#") and len(val) <= 120:
                    canon = _LABEL_CANON.get(label.lower(), label)
                    out.append(val if already else f"{canon}: {val}")
                    i += skip + 1
                    continue
        i += 1
    return "\n".join(out)


def strip_performance(text: str) -> str:
    """Remove return tickers and returns tables so the corpus never offers performance claims."""
    kept = [
        ln for ln in text.splitlines()
        if not _TICKER.search(ln)
        and not _MAX_PCT_LINE.match(ln)
        and not _PERF_LINE.search(ln)
        and not _PURE_PCT.match(ln)
        and not _PURE_RETURNS.match(ln)
    ]
    return join_label_values("\n".join(kept).strip())


def clean_extracted(text: str) -> str:
    return strip_ui_noise(strip_performance(text))


def paragraphize(text: str) -> str:
    """DOM text has one line per element; blank lines make atomic facts detectable."""
    return re.sub(r"\n+", "\n\n", text.strip())


def looks_like_html(text: str) -> bool:
    head = text[:3000].lower()
    return "<html" in head or "<!doctype html" in head or head.lstrip().startswith("<div")


def _clean(text: str) -> str:
    text = (
        text.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    text = _WS.sub(" ", text)
    text = _NL.sub("\n\n", text)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def _tables_to_text(soup: BeautifulSoup) -> None:
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            cells = [c for c in cells if c]
            if cells:
                rows.append(" | ".join(cells))
        if rows:
            table.replace_with("\n" + "\n".join(rows) + "\n")


def _bs4(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "img"]):
        tag.decompose()
    # tooltips sit between a label and its value; dropping them keeps "TER\n0.75" adjacent
    for tag in soup.select('[class*="tooltiptext"], [class*="tooltipcolor"]'):
        tag.decompose()
    for level in range(1, 5):
        for tag in soup.find_all(f"h{level}"):
            tag.insert_before("\n" + "#" * level + " ")
            tag.insert_after("\n")
    for tag in soup.select('[class*="__title"]'):
        text = tag.get_text(" ", strip=True)
        if text and len(text) < 60:
            tag.insert_before("\n### " + text + "\n")
            tag.decompose()
    _tables_to_text(soup)
    return _clean(soup.get_text("\n", strip=True))


def extract(html: str, method: str = "trafilatura", url: str | None = None) -> tuple[str, str]:
    if not looks_like_html(html):
        # reader proxy returned markdown directly
        return clean_extracted(_clean(html)), "reader"
    if method == "trafilatura":
        try:
            import trafilatura

            body = trafilatura.extract(
                html, url=url, output_format="markdown",
                include_tables=True, favor_recall=True,
                include_comments=False,
            )
            if body and len(body) >= 400:
                cleaned = clean_extracted(_clean(body))
                if len(cleaned) >= 2500:
                    return cleaned, "trafilatura"
                # tabbed/accordion pages lose facts in boilerplate removal;
                # DOM text keeps label/value pairs together.
                alt = paragraphize(clean_extracted(_bs4(html)))
                if len(alt) > len(cleaned):
                    return alt, "bs4"
                return cleaned, "trafilatura"
        except Exception:
            pass
    return paragraphize(clean_extracted(_bs4(html))), "bs4"
