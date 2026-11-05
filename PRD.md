# PRD — Mutual Fund FAQs (Facts-Only Q&A)

**Product:** `BuildHourRAG` — a small, citation-backed FAQ assistant for mutual fund schemes
**Source brief:** [`ProblemStatement.txt`](./ProblemStatement.txt)
**Status:** Draft v1
**Owner:** TBD
**Last updated:** 2026-11-05

---

## 1. Summary

Build a working prototype that answers **factual** questions about a small set of mutual fund
schemes (expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, how to
download statements) using **only public official pages**.

Every answer carries **exactly one source link**. Opinionated or portfolio questions are
politely refused with a facts-only message plus an educational link. The system never gives
investment advice, never computes or compares returns, and never accepts or stores PII.

Implementation is **phase-wise and config-driven**: data loading → chunking → embedding →
vector DB, with retrieval reusing the *same* embedding and vector-DB configuration, then a
Groq-hosted LLM for answer composition.

---

## 2. Problem & opportunity

| | |
|---|---|
| **Who** | Retail investors comparing mutual fund schemes; support/content teams answering the same MF questions repeatedly. |
| **Problem** | Answers to basic scheme facts are scattered across AMC factsheets, SEBI/AMFI pages, and platform pages. Users cannot quickly verify a single fact, and generic chatbots hallucinate numbers or slip into advice. |
| **Opportunity** | A narrow, grounded, refusal-capable assistant that is *trustworthy by construction*: small verified corpus, one citation per answer, hard guardrails. |

---

## 3. Goals & non-goals

### Goals
1. Answer the **8 core fact types** accurately from a 15–25 URL curated corpus.
2. Attach **one valid citation** (URL present in the corpus) to 100% of answers.
3. **Refuse** advice/portfolio/performance-comparison queries politely, with an educational link.
4. Keep answers **≤ 3 sentences** and stamp `Last updated from sources: <date>`.
5. Ship a tiny hostable UI (welcome line + 3 example questions + disclaimer).
6. Make every pipeline stage switchable via **one config file** (`config.yaml`), with secrets in `.env`.

### Non-goals
- No returns calculation, ranking, or performance comparison of any kind.
- No portfolio construction, goal planning, or tax advice.
- No user accounts, no transaction flows, no holdings import.
- No coverage beyond the scoped AMC and 3–5 schemes.
- No multi-turn memory of personal data (session is stateless w.r.t. PII).

---

## 4. Scope

### 4.1 Corpus scope (fixed for v1)

**AMC:** HDFC Mutual Fund — *change in `config.yaml → scope.amc` if another AMC is preferred; the corpus manifest must be regenerated.*

**Schemes (4):**

| # | Scheme | Category | Purpose |
|---|--------|----------|---------|
| 1 | HDFC Large Cap Fund | Large Cap | Core equity fact set |
| 2 | HDFC Flexi Cap Fund | Flexi Cap | Core equity fact set |
| 3 | HDFC ELSS Tax Saver Fund | ELSS | Lock-in fact set |
| 4 | HDFC Index Fund – Nifty 50 Plan | Index | Low-cost / benchmark fact set |

> Scheme display names above are the *targets*; exact names and URLs are resolved during
> Phase 1 and frozen in `data/sources.csv`. If a scheme page cannot be sourced from an
> official/allowlisted domain, it is dropped rather than substituted from a blog.

### 4.2 Source tiers

| Tier | Domains | Use |
|------|---------|-----|
| **T1 — Primary citation** | `hdfcfund.com` (AMC), `sebi.gov.in`, `amfiindia.com`, `mfcentral.com` / `kfintech.com` (statement how-tos) | Preferred citation for every factual answer |
| **T2 — Required platform pages** | `indmoney.com` (product, screener, collection, category, blog) | The 6 brief-mandated URLs; citable |
| **T3 — Forbidden** | Any other blog, aggregator, forum, social, screenshot, PDF leaked from a backend | Never ingested, never cited |

**Hard rule:** a URL that is not in `data/sources.csv` must never appear as a citation.

### 4.3 Answerable fact taxonomy (W1)

| Intent | Example user query | Grounding field |
|---|---|---|
| `expense_ratio` | "Expense ratio of HDFC Flexi Cap?" | TER / expense ratio |
| `exit_load` | "Exit load?" | Exit load table |
| `min_sip` | "Minimum SIP amount?" | Min SIP / additional purchase |
| `lock_in` | "ELSS lock-in?" | Lock-in period |
| `riskometer` | "Riskometer level?" | Risk-o-meter |
| `benchmark` | "What is the benchmark?" | Benchmark index |
| `statement` | "How to download capital gains statement?" | Help / how-to page |
| `scheme_meta` | "Fund category? Plans offered?" | Category, plan/option |

### 4.4 Refusal taxonomy

| Intent | Trigger | Behavior |
|---|---|---|
| `advice` | "Should I buy/sell/hold?", "Is it good?" | Refuse + educational link |
| `performance` | "What returns will I get?", "Compare 1Y returns" | Refuse + official factsheet link |
| `portfolio` | "How much should I allocate?", "Rebalance my portfolio" | Refuse + educational link |
| `prediction` | "Will NAV go up?" | Refuse + educational link |
| `out_of_scope` | Scheme/AMC not in corpus | Say not covered + link to scoped index page |
| `pii` | PAN, Aadhaar, account no., OTP, email, phone detected | Reject input, do not log raw text |
| `unknown` | No chunk above threshold | "Not found in my sources" + nearest official link |

---

## 5. User experience

### 5.1 Tiny UI

```
┌──────────────────────────────────────────────────────────────┐
│  Ask a mutual fund fact. I answer from official sources only. │
│  Facts-only. No investment advice.                            │
│                                                               │
│  Try:                                                         │
│   • What is the expense ratio of HDFC Flexi Cap Fund?         │
│   • What is the lock-in period for HDFC ELSS Tax Saver Fund?       │
│   • How do I download my capital gains statement?             │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ Ask a factual question…                              │     │
│  └──────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

**Answer card contract**

```
<answer — max 3 sentences>
Source: <one https:// URL from data/sources.csv>
Last updated from sources: 2026-11-05
```

**Refusal card contract**

```
<polite 1–2 sentence refusal, facts-only>
Here's a factual resource instead: <educational https:// URL>
Last updated from sources: 2026-11-05
```

### 5.2 Disclaimer snippet (used verbatim in the UI footer and README)

> **Facts-only. No investment advice.** This assistant reports publicly available scheme
> facts and links to the official source. It does not recommend, rank, or predict returns.
> Always verify on the AMC/SEBI/AMFI page before acting.

---

## 6. System architecture

```
config.yaml ──► Phase 1 Load ──► Phase 2 Chunk ──► Phase 3 Embed ──► Phase 4 Vector DB
                       │                │                │                 │
                       └── data/raw ────┴── chunks.jsonl ┴── embeddings ───┴── index/
                                                                             │
User query ──► PII gate ──► Intent router ──► (retrieval: same embed + same vDB) ──► LLM ──► Validators ──► UI
                                  │                                                      (Groq)     │
                                  └──► refusal template + educational link ◄──────────────────────────┘
```

### 6.1 Phase 1 — Data loading
- Input: `data/sources.csv` (15–25 rows: `url, title, tier, amc, scheme, doc_type`).
- Fetch with polite defaults (UA string, robots.txt respected, 1.5 s delay, retry/backoff).
- Extract main content; strip nav/footer/cookie banners. Fall back to a headless browser only
  for JS-rendered INDmoney pages (config flag).
- Persist one JSON per URL in `data/raw/` with `url, title, fetched_at, text, content_hash`.
- **Reject** any domain not in the allowlist.
- **Exit criteria:** 15–25 sources parsed; ≥ 90% produce ≥ 500 chars of body text; manifest
  reproducible from a single command.

### 6.2 Phase 2 — Data chunking
- Heading-aware splitting first, then recursive size-based fallback.
- Target 700 tokens, 120 overlap (config), min 120 chars.
- Every chunk carries metadata: `chunk_id, url, title, amc, scheme, doc_type, section, fetched_at`.
- Table-like fact lines (TER, exit load, lock-in) are emitted as **atomic chunks** so a single
  number is never split from its label.
- **Exit criteria:** no chunk without `url` + `scheme`; unit tests assert metadata completeness
  and that fact sentences are intact.

### 6.3 Phase 3 — Embedding
- Default local model `BAAI/bge-small-en-v1.5` (free, no key, fast on CPU).
- Pluggable providers: `openai`, `gemini`, `cohere`, `mistral`.
- Batch embed with progress logging; cache by `content_hash` to avoid re-embedding.
- **Exit criteria:** deterministic embeddings for a fixed chunk set; cache hit on re-run.

### 6.4 Phase 4 — Vector DB
- Default `chroma` (persistent, local, zero-ops). Alternatives: `faiss`, `qdrant`, `pgvector`.
- Collection name, distance metric, and persist dir from config.
- Metadata filters on `amc`, `scheme`, `doc_type`.
- **Exit criteria:** `query("ELSS lock-in", filter={scheme: "HDFC ELSS Tax Saver Fund"})` returns a
  chunk whose URL is the correct scheme page.

### 6.5 Retrieval + generation
- Retrieval **must reuse** Phase 3 embedding config and Phase 4 store config
  (`retrieval.use_same_backend_as_ingestion: true`).
- Hybrid: dense + BM25 (weights configurable), top-k 6, score threshold, optional rerank.
- LLM: **Groq**, model read from `.env` (`GROQ_MODEL`), `temperature: 0`.
- Prompt returns either an answer **with a chosen chunk citation** or a structured refusal.
- Post-generation validators (always on):
  1. citation URL ∈ `data/sources.csv`;
  2. answer ≤ 3 sentences;
  3. no performance/advice tokens (regex + classifier);
  4. `Last updated from sources:` stamp present.
  On failure → single retry → deterministic template fallback.

---

## 7. Configuration

Single source of truth: **`config.yaml`**. No stage may hardcode a model, path, or backend.
Secrets live only in `.env` (git-ignored).

```yaml
app:
  name: "MF Facts Bot"
  disclaimer: "Facts-only. No investment advice."
  max_answer_sentences: 3
  require_citation: true
  ui: "streamlit"                      # streamlit | fastapi

scope:
  amc: "HDFC Mutual Fund"
  schemes:
    - "HDFC Large Cap Fund"
    - "HDFC Flexi Cap Fund"
    - "HDFC ELSS Tax Saver Fund"
    - "HDFC Nifty 50 Index Fund"
  sources_manifest: "data/sources.csv"
  allowlist_domains: ["hdfcfund.com", "sebi.gov.in", "amfiindia.com",
                      "mfcentral.com", "camsonline.com", "kfintech.com", "indmoney.com"]

phases:
  loading:
    fetcher: "jina"                    # jina | curl_cffi | httpx | playwright
    respect_robots_txt: true
    request_delay_ms: 1500
    timeout_s: 30
    retries: 3
    extractor: "trafilatura"           # trafilatura | readability | bs4
    strip_nav_footer: true
    cache_dir: "data/raw"

  chunking:
    strategy: "heading_aware"          # heading_aware | recursive | token
    chunk_size: 700
    chunk_overlap: 120
    min_chunk_chars: 120
    atomic_fact_chunks: true           # never split a number from its label
    dedupe: true
    output: "data/chunks.jsonl"

  embedding:
    provider: "local"                  # local | openai | gemini | cohere | mistral
    model: "BAAI/bge-small-en-v1.5"
    batch_size: 32
    normalize: true
    cache: true

  vectorstore:
    backend: "chroma"                  # chroma | faiss | qdrant | pgvector
    collection: "mf_facts"
    persist_dir: "data/index"
    distance: "cosine"
    reset_on_rebuild: true

retrieval:
  use_same_backend_as_ingestion: true   # needed to match embeddings + store
  embedding_override: null              # set only if retrieval must differ
  vectorstore_override: null
  top_k: 6
  score_threshold: 0.25
  hybrid:
    enabled: true
    dense_weight: 0.65
    bm25_weight: 0.35
  rerank:
    enabled: false
    model: "BAAI/bge-reranker-base"
  filters: ["amc", "scheme", "doc_type"]

llm:
  provider: "groq"                     # groq | gemini | openai | anthropic | mistral
  model_env: "GROQ_MODEL"              # value comes from .env, never hardcoded
  temperature: 0.0
  max_tokens: 350
  timeout_s: 20
  max_retries: 1
  fallback_provider: null              # e.g. "gemini"

guardrails:
  refuse_advice: true
  block_performance_claims: true
  block_pii: true
  pii_types: ["pan", "aadhaar", "account_number", "otp", "email", "phone"]
  max_sentences: 3
  citation_must_be_in_corpus: true
  log_raw_pii: false

logging:
  level: "INFO"
  redact_pii: true
  trace_dir: "data/traces"
```

### `.env` contract

```dotenv
# LLM (default provider: Groq)
GROQ_API_KEY=        # required — rotate any key that has been shared
GROQ_MODEL=          # e.g. the Groq-hosted Qwen model ID from console.groq.com

# Optional alternate providers
GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
MISTRAL_API_KEY=
```

> ⚠️ Verify `GROQ_MODEL` against `console.groq.com/models` at setup. The ID in the brief
> (`qwen/qwen3.8-27b`) does not match a known Groq model string — confirm the exact slug and
> set it in `.env`; the app must fail fast with a clear error if the model is unavailable.

---

## 8. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Accept a single free-text question and return one answer | P0 |
| FR-2 | Answer only the 8 fact intents in §4.3 | P0 |
| FR-3 | Include exactly one citation URL per answer, validated against the manifest | P0 |
| FR-4 | Refuse advice/portfolio/performance/prediction intents politely + educational link | P0 |
| FR-5 | Answer ≤ 3 sentences, plus `Last updated from sources: YYYY-MM-DD` | P0 |
| FR-6 | Welcome line + 3 clickable example questions + disclaimer note | P0 |
| FR-7 | Detect and reject PII inputs without logging the raw value | P0 |
| FR-8 | Redirect performance queries to the official factsheet | P0 |
| FR-9 | Return a graceful "not in my sources" + nearest official link when retrieval misses | P1 |
| FR-10 | Show which scheme the answer applies to when ambiguous | P1 |
| FR-11 | Trace each answer (chunk IDs + scores) to `data/traces/` for audit | P1 |
| FR-12 | Rebuild index with a single CLI command | P1 |

### 8.1 Prompt shape (W2)

```
You are a mutual fund FACT assistant. You never give advice.
Rules:
1. Use ONLY the provided context. If the fact is not present, say so and give the context URL.
2. Answer in at most 3 sentences, neutral tone, no comparisons, no returns.
3. End with exactly one line: Source: <one URL copied verbatim from context metadata>
4. If the question asks for an opinion, recommendation, or portfolio action, reply:
   "I can only share factual scheme information, not investment advice." and add an educational URL.
Context: {retrieved chunks with url + section}
Question: {question}
```

---

## 9. Non-functional requirements

- **Latency:** p95 end-to-end < 4 s (retrieval ≤ 300 ms local; Groq ≤ 2 s).
- **Cost:** ≤ $0.01 per 100 questions at prototype volume; embeddings local by default.
- **Reliability:** graceful degradation — if LLM fails, return the top chunk text + citation.
- **Privacy:** no PII persisted; logs redacted; no user accounts; traces store queries with
  PII redacted.
- **Freshness:** corpus rebuild is a one-command job; every answer surfaces its source date.
- **Reproducibility:** pinned dependencies; seed fixed; config snapshot saved with each index.
- **Portability:** runs locally with only `GROQ_API_KEY` + Python 3.11.

---

## 10. Acceptance criteria & evaluation

| Metric | Target | Method |
|---|---|---|
| Citation validity (URL in manifest) | 100% | Automated check on 50 generated answers |
| Factual accuracy vs. source page | ≥ 95% | Manual review, 5 Q × 8 intents |
| Refusal accuracy (advice/performance) | ≥ 95% | 20 adversarial prompts |
| PII rejection | 100% | 10 synthetic PII prompts |
| ≤ 3 sentence compliance | 100% | Post-processor assertion |
| Retrieval hit@3 on golden set | ≥ 90% | 30-question golden set |
| Answer contains a source date | 100% | Automated check |

**Golden-set categories:** expense ratio, exit load, min SIP, ELSS lock-in, riskometer,
benchmark, statement download, scheme meta, advice refusal, performance refusal,
out-of-scope scheme, PII attempt.

---

## 11. Deliverables mapping

| Brief deliverable | Artifact in this repo |
|---|---|
| Working prototype | `app.py` (Streamlit) deployed link, or `demo.mp4` (≤ 3 min) |
| Source list (15–25 URLs) | `data/sources.csv` + `SOURCES.md` |
| README (setup, scope, limits) | `README.md` |
| Sample Q&A (5–10) | `sample_qa.md` |
| Disclaimer snippet | §5.2, rendered in UI footer |
| Config | `config.yaml` (+ `.env.example`) |

---

## 12. Milestones

| Phase | Deliverable | Exit test |
|---|---|---|
| **0. Setup** | Repo skeleton, `config.yaml`, `.env.example`, manifest with 15–25 URLs | Config loads and validates; manifest passes allowlist |
| **1. Data loading** | `data/raw/*.json` | ≥ 90% of sources yield usable text; hashes stored |
| **2. Data chunking** | `data/chunks.jsonl` | 100% chunks have url/scheme metadata; fact lines intact |
| **3. Data embedding** | Embeddings cached | Re-run hits cache; vectors deterministic |
| **4. Vector DB** | `data/index/` | Filtered query returns correct scheme URL |
| **5. Retrieval + LLM** | Answer endpoint | Golden-set hit@3 ≥ 90%; one citation per answer |
| **6. Guardrails + UI** | Streamlit app | Refusal/PII suites pass; disclaimer visible |
| **7. Docs + demo** | README, SOURCES, sample_qa, video/link | All deliverables present |

---

## 13. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| INDmoney pages are JS-rendered / change layout | Empty or partial corpus | Playwright fallback + `content_hash` drift alert; T1 AMC pages as backup source |
| LLM hallucinates a number | Wrong fact, trust loss | Extractive-first answers; validator rejects any URL not in manifest; numeric tokens checked against context |
| LLM drifts into advice | Compliance breach | Intent router pre-filter + output classifier + deterministic refusal templates |
| Groq model ID invalid / rate limits | No answers | Fail-fast config check; optional `fallback_provider`; retrieval-only degradation |
| Scheme URLs unavailable for scoped AMC | Scope gap | Drop scheme, document in README known limits |
| PII leaks into logs | Privacy breach | Redaction before logging; raw text discarded after request |
| Facts go stale (TER/exit load changes) | Incorrect answers | `fetched_at` surfaced; scheduled rebuild; show source date |

---

## 14. Known limits (v1)

- Only 4 schemes under one AMC; no cross-AMC comparison.
- Statement-download steps may vary by platform; the answer cites the platform help page.
- No NAV history, no returns, no ratings.
- Corpus is a point-in-time snapshot; answers reflect the `Last updated` date.
- English only.

---

## 15. Open questions

1. Confirm the AMC (default HDFC) and final scheme list before Phase 1 freezes.
2. Confirm the exact Groq model slug for `GROQ_MODEL`.
3. Hosting target for the public link: Streamlit Community Cloud vs. Render/Fly.
4. Should the "educational link" for refusals point to SEBI/AMFI investor-education pages (preferred) or INDmoney blog?

---

## Appendix A — Sample Q&A (expected behavior)

| # | Query | Expected |
|---|---|---|
| 1 | What is the expense ratio of HDFC Flexi Cap Fund? | Direct TER fact + scheme-page citation |
| 2 | What is the lock-in for HDFC ELSS Tax Saver Fund? | "3 years" + ELSS scheme citation |
| 3 | Minimum SIP amount? | Amount + source |
| 4 | Exit load if I redeem in 6 months? | Exit-load clause + source |
| 5 | What is the riskometer level? | Risk level + source |
| 6 | Benchmark of HDFC Index Fund – Nifty 50 Plan? | Index name + source |
| 7 | How do I download my capital gains statement? | Steps + help-page citation |
| 8 | Should I buy this fund now? | Refusal + educational link |
| 9 | Which fund gives the best 3-year returns? | Refusal + factsheet link |
| 10 | My PAN is ABCDE1234F — check my account | PII rejection, nothing stored |
