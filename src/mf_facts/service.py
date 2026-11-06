"""Orchestration: PII gate -> intent router -> retrieval -> LLM -> validators."""
from __future__ import annotations

import logging
import os
import re
import time
import uuid
from datetime import date

from mf_facts.contracts import Answer, Chunk, RetrievedChunk
from mf_facts.guardrails import templates
from mf_facts.guardrails.education import EDUCATION_REVIEWED_AT, match_education
from mf_facts.guardrails.intent import (
    FACT,
    REFUSAL,
    Intent,
    detect_scheme,
    route,
)
from mf_facts.guardrails.pii import describe, detect_pii
from mf_facts.guardrails.validators import (
    count_sentences,
    issues,
    truncate_sentences,
)
from mf_facts.llm.prompt import SYSTEM, build_user
from mf_facts.obs.traces import Trace

log = logging.getLogger(__name__)

_SOURCEISH = re.compile(r"^\s*(source|last updated)\s*:", re.I)
_ATOMIC_LABEL = re.compile(
    r"^\s*(Total expense ratio \(TER\)|Total expense ratio|Expense ratio|TER|"
    r"Minimum SIP amount|Min SIP|Minimum SIP|Lock-in period|Lock in|Lock-in|"
    r"Riskometer level|Riskometer|Benchmark index|Benchmark|"
    r"Exit load|Entry load)\s*:\s*(.+)$",
    re.I,
)
_UI_HINTS = ("invest now", "know more", "send email", "download statement\npan")
_FACT_KEYWORDS = {
    "expense_ratio": ("expense", "ter"),
    "exit_load": ("exit load",),
    "min_sip": ("sip", "minimum"),
    "lock_in": ("lock",),
    "riskometer": ("risk",),
    "benchmark": ("benchmark",),
    "statement": ("statement", "download"),
    "scheme_meta": ("category", "plan", "fund manager", "nav", "aum"),
}


def _strip_model_noise(text: str) -> str:
    keep = [ln for ln in text.splitlines() if not _SOURCEISH.match(ln)]
    return "\n".join(keep).strip()


def _sentence_split(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def _plain(text: str) -> str:
    """Drop markdown heading marks / bold marks and collapse whitespace."""
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.M)
    text = text.replace("**", "").replace("|", " ")
    return re.sub(r"\s+", " ", text).strip()


def pick_citation(chunks: list[Chunk], intent: Intent, scheme: str | None) -> Chunk:
    def score(c: Chunk) -> float:
        s = 0.0
        if scheme and c.scheme == scheme:
            s += 8
        if c.fact_type == intent.value:
            s += 4
        if c.is_atomic:
            s += 3
        if _ATOMIC_LABEL.match(c.text):
            s += 2
        low = c.text.lower()
        if intent is Intent.STATEMENT:
            if "download" in low:
                s += 3
            if "you can download" in low:
                s += 4
            if "account statement" in low:
                s += 1
        if intent is Intent.EXIT_LOAD and re.search(r"\d+(?:\.\d+)?\s*%", c.text):
            # the charged percentage is more useful than the "no load after N days" clause
            s += 3
        if (not _ATOMIC_LABEL.match(c.text)
                and len(c.text) < 150 and "." not in c.text):
            s -= 3
        if "disclaimer" in low:
            s -= 2
        if any(hint in low for hint in _UI_HINTS):
            s -= 6
        return s

    return max(chunks, key=score)  # first wins ties, preserving retrieval order


class Service:
    def __init__(self, settings, retriever, llm, manifest):
        self.s = settings
        self.retriever = retriever
        self.llm = llm
        self.manifest = manifest

    # ------------------------------------------------------------------ ask

    def ask(self, question: str) -> Answer:
        started = time.perf_counter()
        trace_id = uuid.uuid4().hex
        hits = detect_pii(question)
        trace = Trace(trace_id, question if not hits else "[REDACTED]", [h.kind for h in hits])

        def done(answer: Answer) -> Answer:
            trace.finish(answer.kind)
            trace.save(self.s.logging.trace_dir, int((time.perf_counter() - started) * 1000))
            return answer

        # 1) PII gate — before any logging or model call
        if hits and self.s.guardrails.block_pii:
            trace.set(intent="pii", route="reject")
            return done(Answer(kind="pii_rejected", text=templates.PII_MESSAGE,
                               trace_id=trace_id))

        # 2) intent router
        intent = route(question, self.s.scope.schemes)
        trace.set(intent=intent.value, route="refusal" if intent in REFUSAL else "rag")

        if intent in REFUSAL:
            return done(Answer(
                kind="refusal",
                text=templates.REFUSALS[intent],
                citation_url=templates.DEFLECTION_LINK[intent],
                updated_at=date.today(),
                trace_id=trace_id,
            ))

        if intent is Intent.OUT_OF_SCOPE:
            return done(Answer(
                kind="refusal",
                text=templates.REFUSALS[Intent.OUT_OF_SCOPE],
                citation_url=templates.DEFLECTION_LINK[Intent.OUT_OF_SCOPE],
                updated_at=date.today(),
                trace_id=trace_id,
            ))

        if intent is Intent.EDUCATION:
            entry = match_education(question)
            if entry is None:
                trace.set(route="not_found")
                return done(Answer(kind="not_found", text=templates.NOT_FOUND_MESSAGE,
                                   trace_id=trace_id))
            trace.set(route="education")
            updated = self.retriever.fetched_at_for(entry.url) or EDUCATION_REVIEWED_AT
            return done(Answer(
                kind="answer",
                text=entry.answer,
                citation_url=entry.url,
                updated_at=updated,
                trace_id=trace_id,
            ))

        if intent is Intent.UNKNOWN:
            trace.set(route="not_found")
            return done(Answer(kind="not_found", text=templates.NOT_FOUND_MESSAGE,
                               trace_id=trace_id))

        # 3) retrieval
        detected = detect_scheme(question, self.s.scope.schemes) \
            if self.s.retrieval.auto_scheme_filter else None
        # statements are platform-level, so do not restrict them to one scheme page
        scheme = None if intent is Intent.STATEMENT else detected
        fact_type = intent.value if intent in FACT else None
        results = self.retriever.retrieve(question, scheme=scheme, fact_type=fact_type)
        trace.set(retrieved=[
            {"chunk_id": r.chunk.chunk_id, "score": round(r.score, 4),
             "url": r.chunk.url, "fact_type": r.chunk.fact_type}
            for r in results
        ])

        if not results:
            trace.set(route="not_found")
            return done(Answer(kind="not_found", text=templates.NOT_FOUND_MESSAGE,
                               trace_id=trace_id))

        chunks = [r.chunk for r in results]
        cite = pick_citation(chunks, intent, scheme)

        # 4) generation: LLM if available, else grounded extractive answer
        text = self._generate(question, chunks, cite, intent)
        trace.set(route="llm" if self.llm else "extractive")

        # 5) validators — fail closed
        for attempt in range(2):
            composed = self._compose(text, cite)
            problems = issues(
                composed, cite.url, self.manifest.is_citable,
                self.s.app.max_answer_sentences,
            )
            trace.set(validation={"attempt": attempt + 1, "problems": problems})
            if not problems:
                break
            if "too_many_sentences" in problems:
                text = truncate_sentences(text, self.s.app.max_answer_sentences)
            else:
                text = self._extractive(cite, intent)
        else:
            text = self._extractive(cite, intent)

        return done(Answer(
            kind="answer",
            text=text,
            citation_url=cite.url,
            updated_at=date.fromisoformat(str(cite.fetched_at)[:10]),
            scheme=None if cite.scheme == "_general" else cite.scheme,
            trace_id=trace_id,
        ))

    # -------------------------------------------------------------- helpers

    def _generate(self, question: str, chunks: list[Chunk], cite: Chunk,
                  intent: Intent) -> str:
        if intent is Intent.STATEMENT:
            # platform-level journey; a fixed grounded answer is safer than prose
            return templates.STATEMENT_ANSWER
        if self.llm is None:
            return self._extractive(cite, intent)
        try:
            result = self.llm.complete(SYSTEM, build_user(question, chunks[:4]))
            text = _strip_model_noise(result.text)
            if not text:
                raise RuntimeError("empty LLM response")
            if "could not find that fact" in text.lower():
                # the model disclaimed despite retrieved evidence; stay grounded
                return self._extractive(cite, intent)
            if re.search(r"https?://|www\.", text, re.I):
                # citations must come only from retrieved metadata, never the model
                return self._extractive(cite, intent)
            return text
        except Exception as exc:  # noqa: BLE001 - degrade, never 500
            log.warning("LLM unavailable (%s); using extractive answer", exc)
            return self._extractive(cite, intent)

    def _extractive(self, chunk: Chunk, intent: Intent) -> str:
        if intent is Intent.STATEMENT:
            return templates.STATEMENT_ANSWER
        text = _plain(chunk.text)
        label = _ATOMIC_LABEL.match(text)
        if label:
            return self._fact_sentence(label.group(1), label.group(2).splitlines()[0], chunk)

        sentences = [s for s in _sentence_split(text) if len(s) > 12]
        if not sentences:
            return text[:300]

        keywords = _FACT_KEYWORDS.get(getattr(intent, "value", ""), ())
        for i, sentence in enumerate(sentences):
            if any(k in sentence.lower() for k in keywords):
                return " ".join(sentences[i:i + 2])[:400]
        return " ".join(sentences[:2])[:400]

    @staticmethod
    def _fact_sentence(label: str, value: str, chunk: Chunk) -> str:
        label = label.strip().lower()
        value = value.strip().rstrip(".")
        for_name = (f" for {chunk.scheme}"
                    if chunk.scheme and chunk.scheme != "_general" else "")
        if label in {"ter", "expense ratio", "total expense ratio",
                     "total expense ratio (ter)"}:
            pct = value if value.endswith("%") else f"{value}%"
            return f"The total expense ratio (TER){for_name} is {pct}."
        if label in {"min sip", "minimum sip", "minimum sip amount"}:
            return f"The minimum SIP amount{for_name} is {value}."
        if label in {"lock in", "lock-in", "lock-in period"}:
            if value.upper() in {"NA", "N/A"}:
                return f"{chunk.scheme or 'This scheme'} has no lock-in period."
            return f"The lock-in period{for_name} is {value}."
        if label in {"riskometer", "riskometer level"}:
            return f"The riskometer level{for_name} is {value}."
        if label in {"benchmark", "benchmark index"}:
            return f"The benchmark{for_name} is {value}."
        if label in {"exit load", "entry load"}:
            if value.upper() in {"NA", "N/A", "NIL", "NONE"}:
                return f"There is no {label}{for_name}."
            return f"The {label}{for_name} is {value}."
        return f"{label}: {value}."

    @staticmethod
    def _compose(text: str, cite: Chunk) -> str:
        return (f"{text.strip()}\n"
                f"Source: {cite.url}\n"
                f"Last updated from sources: {str(cite.fetched_at)[:10]}")


def build_service(settings, strict_llm: bool | None = None) -> Service:
    from mf_facts.ingest.manifest import load_manifest
    from mf_facts.registry import build_embedder, build_llm, build_vectorstore
    from mf_facts.retrieve.retriever import Retriever

    manifest = load_manifest(settings)
    embedder = build_embedder(settings)
    store = build_vectorstore(settings)
    store.ensure_collection(embedder.dim, settings.phases.vectorstore.distance, reset=False)

    retriever = Retriever(settings, store, embedder, manifest)
    retriever.assert_ready()

    strict = os.getenv("MF_FACTS_STRICT_LLM", "0") == "1" if strict_llm is None else strict_llm
    llm = None
    try:
        settings.validate_runtime()
        llm = build_llm(settings)
    except Exception as exc:  # noqa: BLE001
        if strict:
            raise
        log.warning("LLM disabled (%s) — answers will be extractive", exc)

    return Service(settings, retriever, llm, manifest)
