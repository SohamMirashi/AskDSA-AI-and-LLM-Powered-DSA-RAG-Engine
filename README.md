# AskDSA — End-to-End AI & LLM-Powered DSA RAG Engine

> A browser extension that gives **progressive, non-spoiling hints** on Data Structures & Algorithms problems — grounded in a curated knowledge base by a Retrieval-Augmented Generation (RAG) backend and an LLM, deployed on AWS.

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-vector%20search-0467DF)
![Chrome MV3](https://img.shields.io/badge/Chrome-Manifest%20V3-4285F4?logo=googlechrome&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-EC2%20%7C%20S3%20%7C%20CloudWatch-FF9900?logo=amazonaws&logoColor=white)

---

## ✨ What it is

AskDSA helps you **learn** a DSA problem instead of spoiling it. When you open a coding‑practice problem, a floating panel lets you ask for help at four escalating levels:

1. **Nudge** — restates the core of the problem and asks one guiding question.
2. **Strategy** — names the technique/pattern to use (no steps, no code).
3. **Steps** — a step‑by‑step approach with optional pseudocode.
4. **Solution** — the full explanation, complete code, and time/space complexity.

Answers are **grounded** in a knowledge base built from real GeeksforGeeks problems, so the guidance stays relevant rather than generic. If a problem isn't in the knowledge base, the tutor falls back gracefully to the model's own reasoning.

---

## 📦 Installing the extension (Chrome or Edge)

The backend is hosted online, so you only need the extension — nothing else to run.

1. Download and unzip **`AskDSA-extension.zip`** to a folder.
2. Open **`chrome://extensions`**.
3. Turn on **Developer mode** (top‑right toggle).
4. Click **Load unpacked** and select the unzipped **`extension`** folder.
5. Open any **GeeksforGeeks** DSA problem page — the **🎓 AskDSA** button appears at the **bottom‑left**. Click it, pick a hint level (Nudge → Strategy → Steps → Solution), type a question (or leave it blank), and press **Enter**.

> **Tip:** `Enter` sends your question; `Shift + Enter` adds a new line. Each level's answer is cached, so you can switch between levels without losing what you already saw.

---

## 🧠 How it works

```
Browser extension (panel)
      │  HTTPS  POST /tutor   { query, level }
      ▼
Caddy (HTTPS / TLS)  →  FastAPI + Uvicorn
      │
      ├─ RAG engine: embed the query (bge-small) → FAISS vector search
      │   → retrieve the most relevant problem/approach chunks
      │
      └─ LLM (NVIDIA Nemotron, ~300–350B params, via OpenRouter)
          → writes a hint at the requested level, grounded in the retrieved context
      ▼
Answer streamed back into the panel (Markdown rendered; math shown in plain text)
```

- **Grounding** is done by the **problem title** via semantic search, so the tutor finds the closest curated content even when the practice‑page URL differs from the knowledge‑base article.
- The system prompt enforces the **progressive‑hint contract** (each level reveals only as much as asked) and clean, non‑LaTeX formatting for the panel.

---

## 🛠️ Tech stack

| Layer | Technology |
|---|---|
| Extension | Vanilla JavaScript, Chrome **Manifest V3** (content script + service worker), Shadow‑DOM panel |
| Backend API | **Python · FastAPI · Uvicorn** |
| Retrieval | **FAISS** (`IndexFlatIP`, cosine on normalized vectors) |
| Embeddings | **sentence-transformers `BAAI/bge-small-en-v1.5`** |
| LLM | **NVIDIA Nemotron (~300–350B params)** via **OpenRouter** |
| Data collection | **Playwright + BeautifulSoup** |
| Reverse proxy / TLS | **Caddy** (automatic Let's Encrypt HTTPS) |
| Hosting | **AWS** — EC2 (compute), S3 (dataset + index), EBS (storage), IAM (access), CloudWatch (monitoring) |

---

## 📁 Repository structure

```
askdsa/
├── Data Collection/
│   ├── problem_data_scrapper.py   # scrape GfG problem pages → problems.csv
│   └── combine_links.py           # merge per-category link CSVs → all_problem_links.csv
├── rag/
│   ├── chunk.py                   # problems.csv → store/chunks.jsonl (problem + approach chunks)
│   ├── embed.py                   # chunks.jsonl → store/index.faiss + store/meta.pkl
│   ├── retrieve.py                # Retriever: semantic search / direct problem grounding
│   ├── tutor.py                   # progressive-hint tutor (4 levels)
│   └── llm.py                     # OpenRouter (Nemotron) client with retry/backoff
├── api/
│   └── main.py                    # FastAPI app: GET /health, POST /tutor
├── extension/
│   ├── manifest.json              # MV3 config + host permissions
│   ├── background.js              # service worker: calls the backend
│   └── content.js                 # Shadow-DOM panel, 4 levels, Markdown renderer
├── store/                         # index.faiss, meta.pkl, chunks.jsonl
├── problems.csv                   # scraped dataset
└── requirements.txt
```

---

## 🚀 Run the backend locally

Requires Python 3.x and an [OpenRouter](https://openrouter.ai) API key.

```bash
# 1. create a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. install dependencies
pip install fastapi "uvicorn[standard]" pydantic sentence-transformers faiss-cpu numpy requests
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU-only build

# 3. set your key
export OPENROUTER_API_KEY="sk-or-v1-...."   # Windows: set OPENROUTER_API_KEY=...

# 4. run (make sure store/index.faiss and store/meta.pkl exist)
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Test it:
```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/tutor \
  -H "Content-Type: application/json" \
  -d '{"query":"Problem: Kadane. Give me a hint","level":1}'
```

To point the extension at your local backend, set `API_BASE` in `extension/background.js` to `http://127.0.0.1:8000`, add it to `host_permissions` in `extension/manifest.json`, then reload the extension.

---

## 🧩 Building the knowledge base

```bash
# 1. collect problem links (per-category CSVs → one file)
python "Data Collection/combine_links.py"

# 2. scrape each problem page into a wide CSV (throttled; batchable)
python "Data Collection/problem_data_scrapper.py" --limit 100

# 3. turn problems into retrieval chunks
python rag/chunk.py                 # → store/chunks.jsonl

# 4. embed + build the FAISS index
python rag/embed.py                 # → store/index.faiss, store/meta.pkl
```

Chunking produces two chunk types per problem — a **problem** chunk (title + description + examples) and one **approach** chunk per solution approach — and embeds only the text, keeping code in metadata.

---

## ☁️ Deploying to AWS (overview)

The hosted version runs the backend on a single AWS stack:

- **EC2** — an Ubuntu instance runs FastAPI (as a `systemd` service) and Caddy.
- **Caddy** reverse‑proxies to the app and provisions a free **Let's Encrypt** certificate, so the extension can reach it over **HTTPS** (required for browser extensions).
- **S3** stores the scraped dataset and a backup of the FAISS index; the instance reads it through an **IAM role** (no keys on the server).
- **CloudWatch** collects CPU / memory / disk metrics.
- A custom **domain** points to the instance's static IP via DNS A‑records.

Update flow: push code to GitHub → `git pull` on the server → `sudo systemctl restart askdsa`.

---

## ⚙️ Configuration

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | API key used to call the LLM (OpenRouter). Kept server‑side only — never bundled into the extension. |

---

## 🗺️ Roadmap

- More platforms (LeetCode, Codeforces, CodeChef, HackerRank).
- Hybrid retrieval (lexical BM25 + vector) and reranking.
- A relational store for a canonical problem catalog, bookmarks, notes and progress.
- Company‑wise question intelligence with source provenance.
- Related / prerequisite / follow‑up problem recommendations.
- Streaming responses, a formal retrieval/answer‑quality evaluation harness, and Chrome Web Store distribution.

---

## 📝 Notes & limitations

- The knowledge base currently covers **GeeksforGeeks** problems; other sites work best once their content is added.
- Answers are AI‑generated and meant to **assist learning**, not to be copied blindly — always verify code and complexity claims.
- First response after a cold start can be a little slower while the embedding model warms up.
