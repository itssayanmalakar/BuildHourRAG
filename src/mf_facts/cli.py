from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mf_facts.obs.logging import setup_logging
from mf_facts.settings import Settings


def _json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def cmd_doctor(settings) -> int:
    from mf_facts.ingest.manifest import load_manifest
    from mf_facts.vectorstore.fingerprint import compute_fingerprint, read_fingerprint

    ok = True
    print(f"config       : {settings.app.name}")
    print(f"amc          : {settings.scope.amc}")
    print(f"schemes      : {', '.join(settings.scope.schemes)}")

    try:
        manifest = load_manifest(settings)
        print(f"manifest     : {len(manifest.sources)} enabled sources (OK)")
    except Exception as exc:
        ok = False
        print(f"manifest     : FAIL — {exc}")

    raw = list(Path(settings.phases.loading.cache_dir).glob("*.json"))
    chunks = Path(settings.phases.chunking.output)
    n_chunks = sum(1 for _ in chunks.open()) if chunks.exists() else 0
    print(f"raw docs     : {len(raw)}")
    print(f"chunks       : {n_chunks}")

    index_meta = Path(settings.phases.vectorstore.persist_dir) / "index_meta.json"
    if index_meta.exists():
        meta = json.loads(index_meta.read_text())
        stored = read_fingerprint(settings.phases.vectorstore.persist_dir)
        match = stored == compute_fingerprint(settings)
        print(f"index        : {meta['chunks']} vectors, dim={meta['dim']}, "
              f"fingerprint={'OK' if match else 'MISMATCH'}")
        ok = ok and match
    else:
        print("index        : not built")

    key = settings.llm_api_key
    model = settings.llm_model
    print(f"llm          : {settings.llm.provider} / {model or '(missing model)'} / "
          f"key {'set' if key else 'MISSING'}")
    return 0 if ok else 1


def cmd_models(settings) -> int:
    from groq import Groq

    settings.validate_runtime()
    client = Groq(api_key=settings.llm_api_key)
    for m in client.models.list().data:
        print(m.id)
    return 0


def cmd_eval(settings) -> int:
    from mf_facts.guardrails.intent import route
    from mf_facts.guardrails.validators import count_sentences
    from mf_facts.service import build_service

    try:
        import yaml
    except ImportError:
        print("PyYAML required", file=sys.stderr)
        return 2

    path = Path("tests/golden/golden_set.yaml")
    if not path.exists():
        print(f"missing {path}", file=sys.stderr)
        return 2

    service = build_service(settings)
    cases = yaml.safe_load(path.read_text(encoding="utf-8"))
    failures = []

    for case in cases:
        q = case["q"]
        intent = route(q, settings.scope.schemes)
        ans = service.ask(q)
        problems = []

        expected_kind = case.get("kind")
        if expected_kind and ans.kind != expected_kind:
            problems.append(f"kind={ans.kind} expected={expected_kind}")
        expected_intent = case.get("intent")
        if expected_intent and intent.value != expected_intent:
            problems.append(f"intent={intent.value} expected={expected_intent}")
        if ans.kind == "answer":
            if not ans.citation_url:
                problems.append("missing citation")
            if ans.updated_at is None:
                problems.append("missing date")
            if count_sentences(ans.text) > settings.app.max_answer_sentences:
                problems.append("too many sentences")
            if case.get("host") and case["host"] not in (ans.citation_url or ""):
                problems.append(f"host not in {ans.citation_url}")
            if case.get("scheme") and ans.scheme != case["scheme"]:
                problems.append(f"scheme={ans.scheme} expected={case['scheme']}")

        text_low = ans.text.lower()
        for needle in case.get("contains", []):
            if needle.lower() not in text_low:
                problems.append(f"missing text: {needle!r}")
        any_of = case.get("contains_any", [])
        if any_of and not any(n.lower() in text_low for n in any_of):
            problems.append(f"missing any of: {any_of}")
        for needle in case.get("not_contains", []):
            if needle.lower() in text_low:
                problems.append(f"forbidden text: {needle!r}")
        if case.get("citation") and not (ans.citation_url or "").startswith(
            case["citation"]
        ):
            problems.append(f"citation={ans.citation_url} expected prefix={case['citation']}")

        status = "PASS" if not problems else "FAIL"
        print(f"{status}  {q[:70]}")
        if problems:
            failures.append({"q": q, "problems": problems, "answer": ans.card()})

    print(f"\n{len(cases) - len(failures)}/{len(cases)} passed")
    for f in failures:
        print(f"\nFAIL {f['q']}\n  {f['problems']}\n  {f['answer'][:200]}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser("mf-facts")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ingest = sub.add_parser("ingest", help="Phase 1: fetch sources")
    ingest.add_argument("--use-cache", action="store_true")

    sub.add_parser("chunk", help="Phase 2: chunk raw docs")
    sub.add_parser("embed", help="Phase 3: embed chunks")
    sub.add_parser("index", help="Phase 4: build the vector index")

    build = sub.add_parser("build", help="run ingest -> chunk -> embed -> index")
    build.add_argument("--use-cache", action="store_true")

    ask = sub.add_parser("ask", help="ask one question")
    ask.add_argument("question")

    sub.add_parser("eval", help="run the golden set")
    sub.add_parser("doctor", help="report build and config state")
    sub.add_parser("models", help="list the provider's models")
    sub.add_parser("manifest-check", help="validate data/sources.csv")
    sub.add_parser("reset", help="delete index, embed cache and traces")

    args = parser.parse_args(argv)
    settings = Settings.load()
    setup_logging(settings.logging.level, settings.logging.redact_pii)

    if args.cmd == "ingest":
        from mf_facts.ingest.pipeline import run_ingest
        _json(run_ingest(settings, args.use_cache))
    elif args.cmd == "chunk":
        from mf_facts.chunking.pipeline import run_chunk
        _json(run_chunk(settings))
    elif args.cmd == "embed":
        from mf_facts.embedding.pipeline import run_embed
        _json(run_embed(settings))
    elif args.cmd == "index":
        from mf_facts.embedding.store import run_index
        _json(run_index(settings))
    elif args.cmd == "build":
        from mf_facts.chunking.pipeline import run_chunk
        from mf_facts.embedding.pipeline import run_embed
        from mf_facts.embedding.store import run_index
        from mf_facts.ingest.pipeline import run_ingest
        print("== ingest ==");  _json(run_ingest(settings, args.use_cache))
        print("== chunk ==");   _json(run_chunk(settings))
        print("== embed ==");   _json(run_embed(settings))
        print("== index ==");   _json(run_index(settings))
    elif args.cmd == "ask":
        from mf_facts.service import build_service
        service = build_service(settings)
        print(service.ask(args.question).card())
    elif args.cmd == "eval":
        return cmd_eval(settings)
    elif args.cmd == "doctor":
        return cmd_doctor(settings)
    elif args.cmd == "models":
        return cmd_models(settings)
    elif args.cmd == "manifest-check":
        from mf_facts.ingest.manifest import load_manifest
        m = load_manifest(settings)
        print(f"{len(m.sources)} enabled sources, all allowlisted")
    elif args.cmd == "reset":
        import shutil
        for d in (settings.phases.vectorstore.persist_dir,
                  settings.phases.embedding.cache_dir,
                  settings.logging.trace_dir):
            shutil.rmtree(d, ignore_errors=True)
        print("reset ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
