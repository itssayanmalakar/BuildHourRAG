from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class Trace:
    def __init__(self, trace_id: str, question: str, pii: list[str]):
        self.data = {
            "trace_id": trace_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "question": question,
            "pii_detected": pii,
            "intent": None,
            "route": None,
            "retrieved": [],
            "llm": {},
            "validation": {},
            "final_kind": None,
            "latency_ms": None,
        }

    def set(self, **kwargs) -> None:
        self.data.update(kwargs)

    def finish(self, kind: str) -> None:
        self.data["final_kind"] = kind

    def save(self, trace_dir: str, latency_ms: int) -> None:
        self.data["latency_ms"] = latency_ms
        d = Path(trace_dir)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{self.data['trace_id']}.json").write_text(
            json.dumps(self.data, indent=2, default=str), encoding="utf-8"
        )
