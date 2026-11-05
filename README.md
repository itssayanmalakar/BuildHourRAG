# MF Facts Bot

A facts-only mutual fund FAQ assistant built for the INDMoney BuildHour brief.
It answers seven factual intents about a small, fixed set of HDFC Mutual Fund
schemes, cites exactly one official source per answer, refuses advice and
performance questions, and rejects personal data before it is logged or sent to
a model.

The working UI is a Streamlit app (`app.py`); the same pipeline is available
from the CLI.

### Verified in this build

| Check | Result |
|---|---|
| Sources ingested | 19/19 |
| Chunks / vectors | 216 / 216, dim 384, fingerprint OK |
| Unit tests | 52 passed |
| Golden set (Groq enabled) | 35/35 passed |
| Streamlit smoke test | renders answers with citation + date |
| LLM | Groq `qwen/qwen3.8-27b` |

---

## Scope

**AMC:** HDFC Mutual Fund

| Scheme | Page used for scheme facts |
|---|---|
| HDFC Flexi Cap Fund | [Direct plan page](https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/direct) |
| HDFC Large Cap Fund | [Direct plan page](https://www.hdfcfund.com/explore/mutual-funds/hdfc-large-cap-fund/direct) |
| HDFC ELSS Tax Saver Fund | [Direct plan page](https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver-fund/direct) |
| HDFC Nifty 50 Index Fund | [Direct plan page](https://www.hdfcfund.com/explore/mutual-funds/hdfc-nifty-50-index-fund/direct) |

Supported fact intents:

- expense ratio (TER)
- exit load
- minimum SIP
- ELSS lock-in
- riskometer
- benchmark
- how to download a consolidated account statement / capital-gains statement

Also answerable: basic scheme metadata (category, plan, fund manager, NAV, AUM)
when it is present on the scheme page.

**Not answerable by design:** investment advice, fund comparisons, portfolio
allocations, return/CAGR/performance claims, NAV predictions, other AMCs, and
any answer that would require personal data.

The full source list is in [`SOURCES.md`](SOURCES.md): 19 public URLs, including
the six INDMoney pages required by the brief.

---

## How it works

```
data/sources.csv
      │
      ▼
1. Loading      fetch → extract → clean     (src/mf_facts/ingest)
      │          official allowlist, robots.txt, retries/backoff
      ▼
2. Chunking     heading-aware + atomic facts (src/mf_facts/chunking)
      │          performance sections and return tickers stripped
      ▼
3. Embedding    BAAI/bge-small-en-v1.5, 384-dim, cached (src/mf_facts/embedding)
      ▼
4. Vector DB    Chroma, cosine (src/mf_facts/vectorstore)
      ▼
5. Retrieval    scheme filter → fact-type filter → hybrid dense + BM25
      │          reciprocal-rank fusion (src/mf_facts/retrieve)
      ▼
6. Guardrails   PII gate → intent router → fixed refusal copy
      │          citation from retrieved metadata → output validators
      ▼
7. Answer       ≤ 3 sentences + one source + "Last updated from sources" date
                 (src/mf_facts/service.py, app.py)
```

Design choices that matter:

- **Citations are never written by the model.** The URL always comes from the
  retrieved chunk's metadata. The model only drafts the prose.
- **Refusals are pre-LLM.** Advice, portfolio, performance and prediction
  questions are routed deterministically to fixed compliance copy, so a model
  cannot be talked into answering them.
- **PII is rejected before logging or generation.** PAN, Aadhaar, account/folio
  numbers, OTPs, email addresses and phone numbers are detected in the question
  and discarded. Raw PII is never written to traces.
- **Fail closed.** If validation fails (missing source, too many sentences,
  advice/performance tokens, citation outside the manifest), the service falls
  back to a short extractive answer from the cited chunk.
- **Performance is not in the corpus.** Return tickers and performance tables
  are removed at extraction time and performance sections are skipped during
  chunking.

Every stage is configurable in [`config.yaml`](config.yaml): fetcher, extractor,
chunk sizes, embedding model, vector backend, top-k, hybrid weights, LLM
provider/model env var, sentence limit and guardrail toggles. Secrets live only
in `.env`.

---

## Quick start

Requires Python 3.11+ (developed on 3.12).

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Create `.env` from the example and fill in a Groq key:

```bash
cp .env.example .env
# edit .env
```

```dotenv
GROQ_API_KEY=your_key_here
GROQ_MODEL=qwen/qwen3.8-27b
```

> The model slug must exist in your Groq account. Once the key is saved, run
> `python -m mf_facts.cli models` to list the available IDs and put the exact
> one in `GROQ_MODEL`.

Build the corpus and index (first run downloads the embedding model):

```bash
make build          # ingest → chunk → embed → index
make doctor         # verify manifest, chunk count, index, LLM state
```

Run the app:

```bash
make run            # http://localhost:8501
```

Ask from the CLI:

```bash
python -m mf_facts.cli ask "What is the exit load for HDFC Flexi Cap Fund?"
```

Run checks:

```bash
make test           # unit tests (no network/model download)
make eval           # 35-case golden set, incl. refusals and PII
make sources        # regenerate SOURCES.md from data/sources.csv
```

`make` automatically uses `.venv/bin/python` when the venv exists.

---

## Deploy

The app runs locally at <http://localhost:8501> (`make run`). To publish it:

- **GitHub:** create an empty repo and push `main` (commands in
  [`DEPLOYMENT.md`](DEPLOYMENT.md)).
- **Streamlit Community Cloud:** deploy `app.py` from the repo with Python 3.12
  and add `GROQ_API_KEY` + `GROQ_MODEL` as secrets. This is the recommended host.
- **Render/Railway:** same code, container-style start command, two environment
  variables.
- **Vercel:** not supported as-is — Streamlit needs a long-running server, not
  serverless functions. See the re-architecture notes in `DEPLOYMENT.md`.

The prebuilt `data/index/` is committed so the host can start without
re-ingesting the corpus. Full instructions: [`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## Answer contract

Every factual answer has the same shape:

```text
The lock-in period for HDFC ELSS Tax Saver Fund is 3 years.
Source: https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver-fund/direct
Last updated from sources: 2026-11-05
```

- one clear citation link, always from the curated allowlist
- at most three sentences
- a date derived from when the source was fetched
- no return numbers, rankings or recommendations

Answers without a suitable source return a short `not_found` message rather
than guessing. Refusals include one educational link (SEBI / AMFI / AMC).

See [`sample_qa.md`](sample_qa.md) for verified examples.

---

## Configuration

The single source of truth is [`config.yaml`](config.yaml). Useful switches:

| Key | Default | Notes |
|---|---|---|
| `phases.loading.fetcher` | `jina` | `jina` uses `r.jina.ai` to get past Cloudflare; `curl_cffi`, `httpx`, `playwright` also supported |
| `phases.loading.request_delay_ms` | `2500` | politeness delay between fetches |
| `phases.chunking.chunk_size` | `700` | approximate tokens (characters / 4) |
| `phases.embedding.model` | `BAAI/bge-small-en-v1.5` | local, 384-dim |
| `phases.vectorstore.backend` | `chroma` | persisted in `data/index` |
| `retrieval.top_k` | `6` | candidates passed to answer composition |
| `retrieval.hybrid.dense_weight` / `bm25_weight` | `0.65` / `0.35` | normalized RRF fusion |
| `llm.provider` | `groq` | model name is read from `GROQ_MODEL` |
| `app.max_answer_sentences` | `3` | enforced by validators |
| `guardrails.block_pii` | `true` | leave on |

Changing chunking, embedding or vectorstore settings changes the index
fingerprint. Rebuild with `make build` (or `make index` after only re-embedding).

### LLM fallback

If `GROQ_API_KEY` or `GROQ_MODEL` is missing or the API is unreachable, the
service **still answers** using a grounded extractive path: it selects the most
relevant retrieved chunk and turns the atomic label/value into one sentence.
This is what makes the demo usable without a key. Set
`MF_FACTS_STRICT_LLM=1` to fail fast instead.

---

## Corpus notes

- `data/sources.csv` is the editable manifest. It is validated against the
  domain allowlist and the 15–25 URL requirement (`make doctor` /
  `python -m mf_facts.cli manifest-check`).
- Tier 1: HDFC scheme/statement/FAQ/index pages, SEBI, AMFI, MF Central,
  KFintech. Tier 2: the six required INDMoney pages. Anything else is rejected.
- `hdfcfund.com` and `indmoney.com` are Cloudflare-protected, so the default
  loader goes through `r.jina.ai`. The reader proxy is rate-limited; ingest
  uses a 2.5 s delay plus 429 backoff.
- The HDFC TER Excel report (`files.hdfcfund.com/...xls`) returns 403 to
  non-browser clients, so per-scheme TER values are taken from the scheme
  pages instead.
- INDmoney pages are platform/education content. They are required in the
  corpus but cannot supply scheme-specific AMC facts; scheme facts come from
  the HDFC pages.
- `data/raw/`, `data/embed_cache/` and `data/traces/` are build artifacts and
  are gitignored. `data/index/` and `data/chunks.jsonl` are committed so the
  deployed app can start without a rebuild.

### Known limitations

- The live demo needs network access to `r.jina.ai` for a fresh ingest. Once
  built, questions are answered from the local index.
- Scheme facts are point-in-time. The date line reflects the fetch date, not a
  guarantee of real-time accuracy; always re-verify on the linked page.
- Only the four configured schemes are supported. A question about another
  HDFC scheme or AMC is refused as out of scope.
- The LLM is optional; extractive answers are shorter but fully grounded. Only
  the Groq adapter is currently wired; the other provider keys in `.env.example`
  are placeholders for future adapters.
- Statement questions are answered with the HDFC consolidated-account-statement
  route. Capital-gains statements are treated as the same statement journey.

---

## Project layout

```text
config.yaml                 all pipeline settings
data/sources.csv            curated source manifest (19 enabled URLs)
app.py                      Streamlit UI
SOURCES.md                  generated source list
sample_qa.md                verified Q&A examples
src/mf_facts/
  settings.py               typed config + .env loading
  service.py                orchestration and answer composition
  ingest/                   fetch, extract, manifest, pipeline
  chunking/                 atomic fact detection, heading-aware splitter
  embedding/                local embedder, cache, index builder
  vectorstore/              Chroma adapter, fingerprint guard
  retrieve/                 hybrid search, retriever
  llm/                      Groq client and prompts
  guardrails/               PII, intent router, templates, validators
  obs/                      logging and traces
tests/unit/                 52 unit tests
tests/golden/golden_set.yaml 35-case evaluation set
scripts/gen_sources.py      SOURCES.md generator
```

---

## Disclaimer snippet

> **Facts-only. No investment advice.** This assistant reports publicly
> available scheme facts and links to the official source. It does not
> recommend, rank, or predict returns. Mutual fund investments are subject to
> market risks; read all scheme-related documents carefully. Always verify on
> the AMC/SEBI/AMFI page before acting.
