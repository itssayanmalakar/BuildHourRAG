"""Polite HTTP fetching with a browser-like TLS fingerprint or a reader proxy.

`jina` is the default transport because indmoney.com and hdfcfund.com sit behind
Cloudflare bot challenges that reject plain httpx/curl TLS fingerprints. r.jina.ai
is a public reader proxy: it fetches the page server-side and can return the
rendered HTML (so trafilatura can still strip navigation and tickers).
"""
from __future__ import annotations

import random
import time
import urllib.request
from functools import lru_cache
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
BOT_UA = "MFFactsBot/0.1 (educational prototype)"
JINA_PREFIX = "https://r.jina.ai/"


@lru_cache(maxsize=64)
def _robots(host: str, ua: str) -> RobotFileParser | None:
    """Fetch robots.txt with a bounded timeout; allow when it is unavailable."""
    url = f"https://{host}/robots.txt"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
        rp = RobotFileParser()
        rp.set_url(url)
        rp.parse(body.splitlines())
        return rp
    except Exception:
        return None


def robots_allows(url: str, ua: str = BOT_UA) -> bool:
    host = urlparse(url).hostname or ""
    rp = _robots(host, ua)
    return True if rp is None else rp.can_fetch(ua, url)


class FetchError(RuntimeError):
    pass


class Fetcher:
    def __init__(self, cfg):
        self.cfg = cfg
        self._httpx = None

    # ---- transports ----

    def _get_jina(self, url: str) -> tuple[str, int]:
        import httpx

        if self._httpx is None:
            self._httpx = httpx.Client(
                timeout=self.cfg.timeout_s, follow_redirects=True,
                headers={"User-Agent": UA, "Accept-Language": "en-IN,en;q=0.9"},
            )
        r = self._httpx.get(
            JINA_PREFIX + url,
            headers={
                "X-Return-Format": "html",
                "X-Timeout": str(self.cfg.timeout_s),
            },
        )
        return r.text, r.status_code

    def _get_curl_cffi(self, url: str) -> tuple[str, int]:
        from curl_cffi import requests as cffi

        r = cffi.get(
            url, impersonate="chrome", timeout=self.cfg.timeout_s,
            headers={"Accept-Language": "en-IN,en;q=0.9"},
        )
        return r.text, r.status_code

    def _get_httpx(self, url: str) -> tuple[str, int]:
        import httpx

        if self._httpx is None:
            self._httpx = httpx.Client(
                timeout=self.cfg.timeout_s, follow_redirects=True,
                headers={"User-Agent": UA, "Accept-Language": "en-IN,en;q=0.9"},
            )
        r = self._httpx.get(url)
        return r.text, r.status_code

    def _get_playwright(self, url: str) -> tuple[str, int]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=UA)
            resp = page.goto(url, wait_until="networkidle", timeout=45_000)
            html = page.content()
            browser.close()
            return html, resp.status if resp else 0

    def _get_once(self, url: str) -> tuple[str, int]:
        if self.cfg.fetcher == "jina":
            return self._get_jina(url)
        if self.cfg.fetcher == "curl_cffi":
            return self._get_curl_cffi(url)
        if self.cfg.fetcher == "playwright":
            return self._get_playwright(url)
        return self._get_httpx(url)

    # ---- public ----

    def get(self, url: str, needs_js: bool = False) -> tuple[str, int]:
        if self.cfg.respect_robots_txt and not robots_allows(url):
            raise FetchError(f"robots.txt disallows {url}")

        last: Exception | None = None
        for attempt in range(self.cfg.retries):
            try:
                html, status = self._get_once(url)
                if status < 400:
                    return html, status
                last = FetchError(f"HTTP {status}")
                if status == 429:
                    # reader-proxy rate limit: back off harder
                    time.sleep(5 * (attempt + 1))
            except Exception as exc:  # noqa: BLE001 - retried below
                last = exc
            time.sleep((self.cfg.request_delay_ms / 1000) * (2 ** attempt)
                       + random.uniform(0, 0.4))
        raise FetchError(f"{url}: {last}")

    def close(self) -> None:
        if self._httpx is not None:
            self._httpx.close()
