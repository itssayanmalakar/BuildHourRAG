"""Load and validate data/sources.csv. This is the citation allowlist."""
from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import urlparse

from mf_facts.contracts import SourceSpec


class ManifestError(ValueError):
    pass


class Manifest:
    def __init__(self, sources: list[SourceSpec], allowlist: list[str], schemes: list[str]):
        self.all = sources
        self.sources = [s for s in sources if s.enabled]
        self.allowlist = [d.lower().removeprefix("www.") for d in allowlist]
        self.schemes = schemes
        self.urls = {s.url for s in self.sources}
        self._validate()

    @classmethod
    def load(cls, path: str, allowlist: list[str], schemes: list[str]) -> "Manifest":
        p = Path(path)
        if not p.exists():
            raise ManifestError(f"manifest not found: {path}")
        rows: list[SourceSpec] = []
        with p.open(newline="", encoding="utf-8") as fh:
            for raw in csv.DictReader(fh):
                row = {k: (v or "").strip() for k, v in raw.items()}
                row["tier"] = int(row.get("tier") or 2)
                row["enabled"] = row.get("enabled", "true").lower() == "true"
                row["needs_js"] = row.get("needs_js", "false").lower() == "true"
                rows.append(SourceSpec(**row))
        return cls(rows, allowlist, schemes)

    def _validate(self) -> None:
        if not 15 <= len(self.sources) <= 25:
            raise ManifestError(
                f"expected 15-25 enabled sources, found {len(self.sources)}"
            )
        ids = [s.id for s in self.sources]
        urls = [s.url for s in self.sources]
        if len(set(ids)) != len(ids):
            raise ManifestError("duplicate id in manifest")
        if len(set(urls)) != len(urls):
            raise ManifestError("duplicate url in manifest")
        for s in self.sources:
            if not s.url.startswith("https://"):
                raise ManifestError(f"{s.id}: URL must be https")
            host = (urlparse(s.url).hostname or "").lower().removeprefix("www.")
            if not any(host == d or host.endswith("." + d) for d in self.allowlist):
                raise ManifestError(f"{s.id}: domain {host} is not allowlisted")
            if s.scheme != "_general" and s.scheme not in self.schemes:
                raise ManifestError(f"{s.id}: unknown scheme {s.scheme!r}")
            if s.tier not in (1, 2):
                raise ManifestError(f"{s.id}: tier must be 1 or 2")

    def is_citable(self, url: str | None) -> bool:
        return bool(url) and url in self.urls

    def by_scheme(self, scheme: str) -> list[SourceSpec]:
        return [s for s in self.sources if s.scheme == scheme or s.scheme == "_general"]


def load_manifest(settings) -> Manifest:
    return Manifest.load(
        settings.scope.sources_manifest,
        settings.scope.allowlist_domains,
        settings.scope.schemes,
    )
