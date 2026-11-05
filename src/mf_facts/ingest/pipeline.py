"""Phase 1 driver: sources.csv -> data/raw/<id>.json."""
from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from mf_facts.contracts import RawDoc
from mf_facts.ingest.extract import extract
from mf_facts.ingest.fetch import Fetcher
from mf_facts.ingest.manifest import load_manifest

log = logging.getLogger(__name__)


def run_ingest(settings, use_cache: bool = False) -> dict:
    manifest = load_manifest(settings)
    cfg = settings.phases.loading
    out_dir = Path(cfg.cache_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fetcher = Fetcher(cfg)
    ok, failed = 0, []
    try:
        for src in manifest.sources:
            target = out_dir / f"{src.id}.json"
            try:
                html, status = fetcher.get(src.url, needs_js=src.needs_js)
                text, used = extract(html, cfg.extractor, src.url)
                if len(text) < 400:
                    raise ValueError(f"extracted only {len(text)} chars")

                doc = RawDoc(
                    id=src.id, url=src.url, title=src.title, amc=src.amc,
                    scheme=src.scheme, doc_type=src.doc_type, tier=src.tier,
                    fetched_at=datetime.now(timezone.utc), http_status=status,
                    extractor=used, text=text,
                    content_hash="sha256:" + hashlib.sha256(text.encode()).hexdigest(),
                )

                if use_cache and target.exists():
                    prev = RawDoc.model_validate_json(target.read_text(encoding="utf-8"))
                    if prev.content_hash == doc.content_hash:
                        log.info("unchanged  %-28s", src.id)
                        ok += 1
                        continue

                target.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
                ok += 1
                log.info("ok %-30s %6d chars (%s)", src.id, len(text), used)
            except Exception as exc:  # per-source isolation
                failed.append({"id": src.id, "error": str(exc)})
                log.warning("FAIL %-28s %s", src.id, exc)

            if src.needs_js is False:
                time.sleep(cfg.request_delay_ms / 1000)
    finally:
        fetcher.close()

    total = len(manifest.sources)
    ratio = ok / total if total else 0.0
    summary = {"total": total, "ok": ok, "ratio": round(ratio, 3), "failed": failed}
    if ratio < 0.90:
        raise RuntimeError(
            f"ingest success ratio {ratio:.0%} < 90% — fix the failing sources"
        )
    return summary
