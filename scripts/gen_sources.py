"""Generate SOURCES.md from data/sources.csv."""
from __future__ import annotations

import csv
from pathlib import Path

rows = list(csv.DictReader(Path("data/sources.csv").open(encoding="utf-8")))
enabled = [r for r in rows if (r.get("enabled", "true").lower() == "true")]

lines = [
    "# Sources",
    "",
    f"{len(enabled)} public pages used as the corpus. Every answer is cited from this list.",
    "",
    "| # | Source | Scheme | Tier | Type |",
    "|---|---|---|---|---|",
]
for i, r in enumerate(enabled, 1):
    scheme = "All / platform" if r["scheme"] == "_general" else r["scheme"]
    lines.append(
        f"| {i} | [{r['title']}]({r['url']}) | {scheme} | T{r['tier']} | {r['doc_type']} |"
    )
lines += ["", "_Regenerate with `make sources`._", ""]
Path("SOURCES.md").write_text("\n".join(lines), encoding="utf-8")
print(f"SOURCES.md: {len(enabled)} sources")
