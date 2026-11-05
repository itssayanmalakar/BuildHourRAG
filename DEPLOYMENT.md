# Deployment guide

## What exists today

The app is built and runs **locally** as a Streamlit website. There is no public
URL yet because publishing needs your GitHub account (and, for Streamlit Cloud,
your Streamlit account).

Local access:

```bash
cd /Users/macbookair/Documents/GitHub/BuildHourRAG
make run
```

Open <http://localhost:8501>.

The local repository is already initialised and committed (`main`), but it has
no GitHub remote yet.

---

## 1. Connect the project to GitHub

### Option A — create the repo on github.com, then push

1. Create an **empty** repository at <https://github.com/new>.
   Do **not** add a README, `.gitignore` or licence (the project already has
   them, and an initialised remote causes a merge conflict).
2. Copy the repository URL, then run:

```bash
cd /Users/macbookair/Documents/GitHub/BuildHourRAG
git remote add origin https://github.com/<your-user>/<repo>.git
git push -u origin main
```

If GitHub asks for a password, use a **personal access token** (Settings →
Developer settings → Personal access tokens), not your account password. Or use
SSH:

```bash
git remote add origin git@github.com:<your-user>/<repo>.git
git push -u origin main
```

### Option B — GitHub CLI (one command)

`gh` is not installed on this machine. If you want the CLI flow:

```bash
brew install gh
gh auth login
cd /Users/macbookair/Documents/GitHub/BuildHourRAG
gh repo create BuildHourRAG --public --source=. --remote=origin --push
```

### What is committed

- source, config, docs and tests
- `data/sources.csv` and `data/chunks.jsonl`
- `data/index/` (2.3 MB Chroma index) so a host can start without re-ingesting

Excluded by `.gitignore`: `.env`, `.venv/`, `data/raw/`, `data/embed_cache/`,
`data/traces/`, `.streamlit/secrets.toml` and `*.egg-info/`.

**Never commit `.env`.** The Groq key stays local and is added as a host secret.

---

## 2. Deploy

### Recommended: Streamlit Community Cloud (free)

This is the native host for a Streamlit app and the shortest path from GitHub.

1. Push the repo to GitHub (section 1).
2. Go to <https://share.streamlit.io> and sign in with GitHub.
3. Click **New app** → **Deploy a public app from GitHub**.
4. Select:
   - Repository: `<your-user>/<repo>`
   - Branch: `main`
   - Main file path: `app.py`
5. Open **Advanced settings** → **Python version** → choose **3.12**.
6. In **Secrets**, paste:

```toml
GROQ_API_KEY = "gsk_your_new_key"
GROQ_MODEL = "qwen/qwen3.8-27b"
```

7. Click **Deploy**.

The app reads Streamlit secrets through the bridge in `app.py`, so the same code
works locally (`.env`) and on Cloud (`st.secrets`).

First load downloads the embedding model `BAAI/bge-small-en-v1.5` (~130 MB) and
then loads the committed Chroma index. Allow 1–3 minutes for the first page
load; later loads are fast.

Your public URL will look like:

```text
https://<app-name>.streamlit.app
```

`requirements.txt` is pinned and `packages.txt` adds `libgomp1` for PyTorch.

#### Redeploying after a corpus change

The index fingerprint must match `config.yaml`. If you change chunking,
embedding or vector settings:

```bash
make build
git add data/index data/chunks.jsonl
git commit -m "Rebuild index"
git push
```

Streamlit Cloud redeploys automatically on push (or use **Reboot app**).

---

### Alternative: Render / Railway (container-style host)

Use this if you need a custom domain, a persistent disk or more control.

**Render Web Service settings:**

- Runtime: Python 3.12
- Build command:
  ```bash
  pip install -r requirements.txt && pip install -e .
  ```
- Start command:
  ```bash
  streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
  ```
- Environment variables:
  ```text
  GROQ_API_KEY=...
  GROQ_MODEL=qwen/qwen3.8-27b
  ```
- The committed `data/index/` means no ingest is needed at boot.

Railway and Fly.io work the same way: use the start command above, set the two
environment variables, and expose the HTTP port.

---

## 3. Vercel: why it does not fit

**Vercel cannot run this app as-is.** Vercel hosts static sites and short-lived
serverless/edge functions. Streamlit needs a long-running Python server with
WebSocket sessions, a local TF-IDF/BM25 index and a persistent Chroma store.
There is no native Streamlit runtime on Vercel, and serverless function limits
break the model load and the vector store.

You have three realistic choices:

1. **Deploy on Streamlit Community Cloud** (recommended, free, no rewrite).
2. **Deploy on Render/Railway** (same code, custom domain, paid/free tiers).
3. **Rebuild for Vercel** — a different architecture:
   - Next.js frontend on Vercel
   - Python/Node API on Render or Vercel Functions
   - embeddings from a hosted API (OpenAI/Gemini/Cohere)
   - vector store hosted (Pinecone, Qdrant Cloud, Upstash Vector)
   - Groq called from the serverless function

That rewrite is a separate project and is not required by the brief. A static
landing page *can* be hosted on Vercel, but the FAQ assistant itself cannot.

---

## 4. Post-deploy checklist

- [ ] Open the public URL and ask one fact from each of the 7 intents.
- [ ] Confirm each answer has exactly one source link and a date.
- [ ] Ask an advice question and confirm the refusal + educational link.
- [ ] Ask an out-of-scope AMC question and confirm the refusal.
- [ ] Try a PAN/email/phone question and confirm `pii_rejected`.
- [ ] Confirm `GROQ_MODEL` exists in the host account (`python -m mf_facts.cli models`).
- [ ] Rotate the Groq key that was shared in chat, then update the host secret.
- [ ] Keep `data/index/` and `config.yaml` in sync; rebuild if either changes.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `index fingerprint mismatch` | Run `make build`, commit `data/index`, push |
| `Missing from .env: GROQ_API_KEY...` | Add the secret in the host dashboard, then reboot |
| First load very slow / times out | Model download on first boot; retry once |
| `No module named mf_facts` | Host build must include `pip install -e .` |
| Streamlit Cloud install fails on torch | Confirm `packages.txt` contains `libgomp1` and Python 3.12 |
| Chroma DB version error | Keep `chromadb==1.1.1` in `requirements.txt` and rebuild the index |
