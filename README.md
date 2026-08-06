<div align="center">

# ⚖️ Reducing Hallucinations in Legal AI Using Retrieval-Augmented Generation

**A Production-Grade, Citation-Verified Legal Question-Answering System**

---

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-EA2845?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Paper](https://img.shields.io/badge/IEEE-Paper-ready-green)](docs/research/paper.md)

**College Mini Project · IEEE Research Paper · Portfolio Showcase · AI Startup Blueprint**

</div>

---

## 📚 Table of Contents

- [Project Overview](#-project-overview)
- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Folder Structure](#-folder-structure)
- [Tech Stack](#-tech-stack)
- [Development Phases](#-development-phases)
- [Project Workflow](#-project-workflow)
- [AI Pipeline](#-ai-pipeline)
- [Installation](#-installation)
- [Environment Variables](#-environment-variables)
- [Running the Project](#-running-the-project)
- [Future Scope](#-future-scope)
- [Research Contributions](#-research-contributions)
- [Startup Vision](#-startup-vision)
- [References](#-references)

---

## 🎯 Project Overview

### What Problem Does It Solve?

Large Language Models (LLMs) are extraordinarily fluent but **fundamentally unreliable** when asked legal questions. They generate answers that *sound* authoritative while quietly inventing case names, fabricating statute numbers, and misquoting precedents. In a domain where a single wrong citation can result in sanctions, overturned rulings, or a destroyed career, this failure mode is **unacceptable**.

This project builds a **Legal Question-Answering (LQA) system** that:

1. Answers legal questions grounded *exclusively* in an ingested legal corpus.
2. Attaches **verifiable citations** to every factual claim.
3. Detects and **flags hallucinated content** before it reaches the user.
4. Assigns a **confidence score** so users know how much to trust each answer.

### Why Does Legal AI Hallucinate?

| Root Cause | Explanation |
|---|---|
| **Fluency over factuality** | LLMs are trained to predict the *next token*, not to be *right*. Legal prose is a statistically likely continuation — even when invented. |
| **Parameterized memorization** | Models memorize training data as weights. If a statute changed or a case was overruled, the model confidently recites **outdated law**. |
| **Legalese ambiguity** | Legal language is dense, context-dependent, and precedential. Ambiguity increases the entropy of plausible continuations. |
| **Rare and tail knowledge** | Most legal knowledge is long-tail. LLMs are weakest exactly where a lawyer works hardest — niche statutes and obscure precedent. |
| **No ground truth binding** | Without an external source to check against, there is nothing stopping the model from confabulating. |

### Why Is RAG Alone Insufficient?

Naive RAG — *embed chunks → retrieve top-k → stuff into prompt* — has well-documented failure modes that are **fatal in legal settings**:

| Naive RAG Failure | Consequence in Legal AI |
|---|---|
| **Semantic chunking** splits a section right through a statutory definition or a multi-part test | Retrieved context is **incomplete**, producing wrong legal tests |
| **Pure dense retrieval** misses exact-case references, docket numbers, § symbols | Key precedent **never surfaces** from the corpus |
| **Retrieval is silent** — no provenance attached to tokens | The user **cannot verify** where the answer came from |
| **LLM is free to paraphrase beyond the evidence** | The model **drifts from the source**, producing near-citations |
| **No post-generation check** | Fabrications are **delivered with confidence** |
| **No uncertainty quantification** | Users cannot distinguish **law from guess** |

> A lawyer cannot cite a retrieval system. A lawyer cites **a case, a statute, a paragraph**. RAG alone does not guarantee any of these exist in the retrieved text.

### Why Is This Architecture Better?

This project treats hallucination as an **engineering problem with multiple defense layers**, not a single-model fix:

1. **Summary-Augmented Chunking** — each chunk is fused with a semantic summary of its parent section, so retrieval never loses the legal context that chunk boundaries destroy.
2. **Hybrid Retrieval (BM25 + Dense)** — lexical matching finds exact statutes and case names; dense embeddings find semantically similar rulings. Combined, they recover what either alone would miss.
3. **Re-ranking** — a cross-encoder scores candidates against the question, keeping only the strongest evidence.
4. **Citation Verification** — the system cross-checks every citation claim against the actual retrieved source text using NLI-style entailment and string/entity matching.
5. **Hallucination Detection** — a dedicated classifier (NLI entailment + fact-consistency scoring) flags claims that are not supported by evidence.
6. **Explainable Responses + Confidence Scoring** — every answer arrives with provenance, a source map, and a calibrated trust score.

The result is an **evidence-first, self-auditing legal assistant** that makes hallucination *visible, measurable, and defensible*.

---

## ✨ Features

### 1. PDF Ingestion & Semantic Parsing

- Supports scanned and digital PDFs, DOCX, TXT, and HTML sources.
- Layout-aware parsing (PyMuPDF / pdfplumber) preserves headings, footnotes, section numbers, and page boundaries — critical for legal citations.
- Incremental ingestion: the index only rebuilds for changed documents.

### 2. Text Cleaning & Normalization

- Removes page furniture, running headers, and OCR noise.
- Normalizes typographic characters (`§`, `–`, curly quotes) into canonical forms so § searches and citations match.
- Preserves legal markup: sub-clauses, numbered lists, and cross-references.

### 3. Metadata Extraction

- Automatically extracts `Act / Case Name`, `Year`, `Court`, `Jurisdiction`, `Section`, `Citation`, and `Document ID`.
- Metadata is stored alongside embeddings and used as **filterable facets** during retrieval (e.g., "only Indian Penal Code, 1860, § 300").

### 4. Summary-Augmented Chunking ⭐

The core innovation:

- Documents are segmented into **hierarchical blocks** (section → subsection → paragraph).
- Each chunk is stored as a **triplet**:
  - `chunk_id`
  - `chunk_text` — the raw paragraph-level snippet
  - `summary_augment` — a compressed semantic summary of the parent section
- At retrieval time, both the snippet *and* its augment are embedded. This **recovers context lost at chunk boundaries** — a known failure of naive RAG.
- Chunk size, overlap, and summary strategy are configurable.

### 5. Dense Embeddings

- Semantic embeddings generated with a fine-tuned sentence-transformer (e.g., `all-MiniLM-L6-v2`, `bge-base-en-v1.5`, or `multilingual-e5-large`).
- Embedding model is pluggable; a `legal-embeddings` fine-tune step is provided.

### 6. Hybrid Retrieval (BM25 + Dense)

- **BM25 lexical retrieval** over the raw chunk text — captures exact § references, case names, and docket numbers.
- **Dense vector search** — captures semantic similarity to paraphrases and conceptually related rulings.
- Both result sets are fused via **Reciprocal Rank Fusion (RRF)**, followed by a **cross-encoder re-ranking** pass.

### 7. Qdrant Vector Database

- Purpose-built vector DB with built-in **HNSW** indexing.
- Supports **metadata payload filtering** (court, year, section) for facet-aware search.
- Scales to millions of chunks; supports hybrid + full-text queries natively.

### 8. Citation Verification

- Every factual claim in the LLM response is parsed into **claim + citation** pairs.
- A pipeline verifies that:
  - The cited source **exists** in the corpus (entity + string matching against metadata).
  - The claim is **entailed** by the cited source text (NLI scoring).
- Unverifiable citations are **struck through** and reported, never silently dropped.

### 9. Hallucination Detection

- Post-generation **fact-consistency check** using NLI entailment between each generated claim and the retrieved evidence.
- Heuristic checks for fabricated case names, statutory sections, and page references.
- Each claim is labeled `SUPPORTED` / `CONTRADICTED` / `UNVERIFIABLE`.

### 10. Explainable Responses

- Every answer ships with a **Sources panel**: chunk IDs, source documents, page/section numbers, and the exact passages used.
- Answers render as **claim-by-claim** panels with per-claim evidence, so a user can trace each sentence to its authority.

### 11. Confidence Scoring

- A calibrated confidence score (0–1) per answer, derived from:
  - Retrieval scores (hybrid fusion + re-ranker)
  - Citation verification pass rate
  - Hallucination-detection entailment margins
- Low-confidence answers are **flagged** with a warning banner rather than being presented as fact.

### 12. Interactive Web App & REST API

- FastAPI backend exposing `/api/ingest`, `/api/search`, `/api/query`, `/api/conversations/chat`, `/api/health`, plus auth and admin routes.
- Next.js 15 web app with streaming chat, source search, document ingestion, settings, admin, and public share links.
- Swagger/OpenAPI docs auto-generated at `/docs`.

### 13. Evaluation & Benchmarking Suite

- Golden question–answer sets with ground-truth citations.
- Metrics: **Faithfulness**, **Answer Relevance**, **Context Precision/Recall**, **Citation Accuracy**, and **Hallucination Rate**.
- A/B comparison against a baseline naive-RAG system.

---

## 🏗 System Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                                    │
│                    Web UI (Next.js) · REST API · CLI                       │
└───────────────────────────────────┬────────────────────────────────────────┘
                                    │ HTTP / JSON
┌───────────────────────────────────▼────────────────────────────────────────┐
│                            API / SERVICE LAYER                             │
│                        FastAPI · Auth · Rate Limiting                      │
└───────────────┬───────────────────────────────────┬────────────────────────┘
                │                                   │
    ┌───────────▼───────────┐           ┌───────────▼───────────┐
    │  INGESTION SERVICE    │           │  INFERENCE SERVICE    │
    │  (Offline Pipeline)   │           │   (Online Serving)    │
    │                       │           │                       │
    │  Parser ── Cleaner ── │           │  Hybrid Retriever     │
    │  Metadata Extractor   │           │   (BM25 + Dense)      │
    │  Summarizer           │           │  Re-ranker            │
    │  Chunker             │           │  LLM Generator         │
    │  Embedder            │           │  Citation Verifier     │
    └───────────┬───────────┘           │  Hallucination Guard   │
                │                       │  Confidence Scorer     │
                │                       └───────────┬───────────┘
                │                                   │
┌───────────────▼───────────────────────────────────▼────────────────────────┐
│                          DATA / INFRASTRUCTURE LAYER                        │
│  ┌──────────────────────────┐   ┌─────────────────────────────────────┐    │
│  │  Qdrant Vector Database  │   │  PostgreSQL / Redis (Cache · KV)    │    │
│  │  · HNSW vectors          │   │  · Ingestion jobs · Audit logs      │    │
│  │  · BM25 full-text index  │   │  · Cache of frequent queries        │    │
│  │  · Metadata payloads     │   │                                     │    │
│  └──────────────────────────┘   └─────────────────────────────────────┘    │
│                                                                              │
│  ┌──────────────────────────┐   ┌─────────────────────────────────────┐    │
│  │  Object Storage (MinIO)  │   │  Model Registry (MLflow)            │    │
│  │  · Raw PDFs · Deltas     │   │  · Embedder · Re-ranker · LLM       │    │
│  └──────────────────────────┘   └─────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Key design principles:**

- **Ingestion and inference are decoupled** — re-indexing never blocks query serving.
- **Everything is observable** — every step emits structured logs and evaluation metrics.
- **Every component is pluggable** — swap the embedder, retriever, or LLM without rewriting the pipeline.

---

## 📁 Folder Structure

```
.
├── app/                          # FastAPI backend
│   ├── main.py                   # App entrypoint, middleware, routers, lifespan
│   ├── config.py                 # Pydantic-settings based configuration
│   ├── api/
│   │   ├── routes/
│   │   │   ├── auth.py           # register / login / refresh / logout / me
│   │   │   ├── conversations.py  # CRUD, pin, search, export, share
│   │   │   ├── chat.py           # non-stream + streaming chat, persists exchanges
│   │   │   ├── share.py          # public GET /api/share/{slug}
│   │   │   ├── admin.py          # users, stats, metrics (admin-only)
│   │   │   ├── ingest.py         # /api/ingest, /api/index, /api/jobs
│   │   │   ├── search.py         # POST /api/search (hybrid retrieval)
│   │   │   ├── generation.py     # POST /api/query (stateless generation)
│   │   │   └── health.py         # GET /api/health
│   │   ├── dependencies.py       # DI for retriever / pipeline / settings
│   │   ├── security_deps.py      # auth guards, rate limiter
│   │   └── schemas.py            # Pydantic request/response models
│   ├── core/                     # security, ratelimit, metrics, middleware
│   ├── db/                       # SQLAlchemy models (users, conversations, messages)
│   ├── repositories/             # memory + postgres implementations
│   ├── services/                 # auth, conversations, jobs, auto-ingest watcher
│   ├── ingestion/                # parser, cleaner, chunker, embedder, pipeline
│   ├── retrieval/                # hybrid (BM25 + dense), reranker
│   └── generation/               # LLM clients, generation pipeline, verification
│
├── frontend/                     # Next.js 15 web app (TypeScript + Tailwind)
│   ├── app/                      # App Router pages (chat, search, admin, ...)
│   ├── components/               # UI primitives + chat components
│   ├── stores/                   # Zustand stores (auth, chat, settings)
│   ├── lib/                      # API client, types, utils
│   ├── tests/                    # Vitest + Testing Library
│   ├── Dockerfile / nginx.conf   # standalone Next build served behind nginx
│   └── package.json
│
├── tests/                        # Backend test suite (Pytest)
├── alembic/                      # Database migrations
├── data/
│   ├── raw/                      # Source documents (gitignored)
│   └── raw_documents/            # Auto-ingest watch directory
│
├── docker-compose.yml            # qdrant + postgres + redis + api + web
├── Dockerfile                    # Backend image
├── pyproject.toml                # Python deps + dev tooling
├── .env.example
└── README.md
```

---

## 🛠 Tech Stack

| Layer | Technology | Why It Was Chosen |
|---|---|---|
| **Language** | Python 3.10+ | De facto standard for NLP/ML; richest ecosystem of legal-NLP and RAG tooling |
| **API Framework** | FastAPI + Uvicorn | Async, typed, auto-generated OpenAPI docs; production-grade and easy to demo |
| **Web Frontend** | Next.js 15 + React 19 + TypeScript + Tailwind CSS | Server components, streaming UI, static export for the landing pages |
| **State / Data Fetching** | Zustand + Axios | Lightweight global state and an API client with auth, CSRF, and token refresh |
| **PDF Parsing** | PyMuPDF / pdfplumber | Layout-aware extraction that preserves headings, page numbers, and section structure |
| **Dense Embeddings** | Sentence-Transformers (`bge-base-en-v1.5`) | Strong semantic retrieval, multilingual support, fine-tunable on legal corpus |
| **Lexical Retrieval** | BM25 (Qdrant full-text or local `rank-bm25`) | Exact matching for § symbols, case names, and citations that vectors miss |
| **Vector Database** | Qdrant | High-performance HNSW indexing, native payload filtering, hybrid search, easy Docker deploy |
| **Re-ranking** | Cross-Encoder (`cross-encoder/ms-marco-MiniLM-L6-v2`) | Precision re-scoring of candidates for final evidence selection |
| **LLM** | Pluggable: `claude` / `openai` / `gemini` / `llama` / `mock` | Generation is provider-agnostic; `mock` runs offline with zero API keys |
| **Metadata Store** | PostgreSQL 16 + SQLAlchemy (async) + Alembic | Users, conversations, messages, share links, API usage |
| **Cache / Rate Limit** | Redis | Rate limiting and caching, with an automatic in-memory fallback |
| **Auth** | JWT + refresh-token rotation, bcrypt, CSRF, HttpOnly cookies | Session-safe auth with cookie/CSRF defaults for a web app |
| **Monitoring** | Prometheus | `/metrics` endpoint for HTTP/LLM/retrieval counters |
| **Orchestration** | Docker Compose | One-command environment with Qdrant, Postgres, Redis, API, and web |
| **Evaluation** | RAGAS-style metrics + verification/hallucination scorers | Faithfulness, relevance, citation accuracy, and hallucination rate |
| **CI** | GitHub Actions | Backend tests + lint, frontend typecheck/test/build, Docker builds |

---

## 🗺 Development Phases

### Phase 0 — Foundations *(Week 1)*
- Set up repo, Docker, linting, CI skeleton.
- Implement PDF parser + text cleaner.
- Unit tests for parsing edge cases.

### Phase 1 — Ingestion Pipeline *(Week 2)*
- Metadata extraction.
- Baseline chunker.
- Embedder + Qdrant schema.
- Bulk ingestion CLI. ✅ *Milestone: searchable legal corpus*

### Phase 2 — Hybrid Retrieval *(Week 3)*
- BM25 + dense retrieval.
- Reciprocal Rank Fusion.
- Cross-encoder re-ranking.
- Retrieval evaluation (recall@k, precision@k). ✅ *Milestone: strong retrieval*

### Phase 3 — Generation + Verification *(Week 4)*
- Prompt engineering with citations.
- Claim + citation extraction.
- Citation verification pipeline.
- Hallucination detection (NLI). ✅ *Milestone: citation-verified answers*

### Phase 4 — Confidence + Explainability *(Week 5)*
- Confidence scoring model.
- Evidence panels + warning banners.
- Next.js UI. ✅ *Milestone: demo-ready system*

### Phase 5 — Evaluation & Ablation *(Week 6)*
- Golden dataset construction.
- Baseline naive-RAG comparison.
- Ablation: with/without summary-augmented chunking, hybrid retrieval, verification.
- IEEE paper draft + experiments write-up. ✅ *Milestone: research-ready results*

### Phase 6 — Hardening & Deployment *(Week 7–8)*
- Async ingestion, caching, rate limiting.
- Docker Compose production profile.
- Documentation, API polish, portfolio demo video. ✅ *Milestone: production-style release*

---

## 🔄 Project Workflow

```
                        ┌──────────────────────────┐
                        │    LEGAL PDF / DOCX      │
                        └────────────┬─────────────┘
                                     ▼
                        ┌──────────────────────────┐
                        │  1. INGEST DOCUMENT      │
                        │   (parser + metadata)    │
                        └────────────┬─────────────┘
                                     ▼
                        ┌──────────────────────────┐
                        │  2. CLEAN + NORMALIZE    │
                        └────────────┬─────────────┘
                                     ▼
                        ┌──────────────────────────┐
                        │  3. SUMMARY-AUGMENTED    │
                        │       CHUNKING           │
                        └────────────┬─────────────┘
                                     ▼
                        ┌──────────────────────────┐
                        │  4. EMBED + STORE        │
                        │     (Qdrant + BM25)      │
                        └──────────────────────────┘
                                     ▲
                                     │  query
                        ┌────────────┴─────────────┐
                        │  5. HYBRID RETRIEVAL     │
                        │   (BM25 + Dense + RRF)   │
                        └────────────┬─────────────┘
                                     ▼
                        ┌──────────────────────────┐
                        │  6. RE-RANK (Top-K)      │
                        └────────────┬─────────────┘
                                     ▼
                        ┌──────────────────────────┐
                        │  7. LLM GENERATION       │
                        │  (grounded + cited)      │
                        └────────────┬─────────────┘
                                     ▼
                        ┌──────────────────────────┐
                        │  8. CLAIM EXTRACTION     │
                        └────────────┬─────────────┘
                                     ▼
                        ┌──────────────────────────┐
                        │  9. CITATION VERIFY +    │
                        │     HALLUCINATION CHECK  │
                        └────────────┬─────────────┘
                                     ▼
                        ┌──────────────────────────┐
                        │ 10. CONFIDENCE SCORE     │
                        └────────────┬─────────────┘
                                     ▼
                        ┌──────────────────────────┐
                        │  11. FINAL RESPONSE      │
                        │  + sources + evidence    │
                        └──────────────────────────┘
```

**User experience loop:** *ask → system retrieves only from your corpus → answer with per-claim citations → verification badges → confidence gauge → view raw source passages.*

---

## 🧠 AI Pipeline

```
PDF
 ↓
Parser                 → extract text, structure, page numbers
 ↓
Cleaning               → strip headers/OCR noise, normalize glyphs
 ↓
Metadata Extraction    → act/case, year, court, section, citation
 ↓
Chunking               → hierarchical, overlap-aware blocks
 ↓
Summary Generation     → semantic summary of each parent section
 ↓
Embedding              → dense vectors for (chunk + summary augment)
 ↓
Qdrant                 → HNSW index + payload facets + BM25 index
 ↓
Hybrid Retrieval       → dense neighbors ⊕ BM25 hits → RRF fusion
 ↓
Re-ranking             → cross-encoder precision scoring → top-k
 ↓
LLM                    → evidence-grounded, citation-marked answer
 ↓
Citation Verification  → claim↔source entailment + citation existence
 ↓
Hallucination Detection→ SUPPORTED / CONTRADICTED / UNVERIFIABLE
 ↓
Confidence Score       → calibrated 0–1 trust estimate
 ↓
Final Response         → answer + citations + sources + confidence
```

---

## 📦 Installation

### Prerequisites

- **Python 3.10+** (developed on 3.14)
- **Node.js 20+** and npm (for the Next.js frontend)
- **Docker + Docker Compose** (for Qdrant, PostgreSQL, Redis, and the full stack)
- `pip` and a virtual environment

### 1. Clone the Repository

```bash
git clone https://github.com/vvvvvivekkk/-hallucination-legal-ai.git
cd -hallucination-legal-ai
```

### 2. Backend — Virtual Environment & Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

pip install --upgrade pip
pip install -e ".[dev]"
```

### 3. Frontend — Install npm Dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Configure Environment

```bash
cp .env.example .env
# edit .env with your LLM API key and settings (see below)
```

### 5. Start the Infrastructure (Qdrant + PostgreSQL + Redis)

```bash
docker compose up -d qdrant postgres redis
```

### 6. Apply Database Migrations

```bash
alembic upgrade head
```

### 7. Ingest Your Legal Corpus

Place source documents in `data/raw_documents/` (watched automatically) or `data/raw/`, then
queue an ingestion job through the API:

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"path": "data/raw_documents"}'
```

Track progress at `GET /api/jobs`.

### 8. Launch the Backend API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive docs: **http://localhost:8000/docs**

### 9. Launch the Web Frontend

```bash
cd frontend
npm run dev
```

Open **http://localhost:3000**

---

## 🔐 Environment Variables

The full list lives in [`.env.example`](.env.example) — copy it to `.env` and edit. The most
important settings:

```bash
# ── LLM (mock needs no API key) ────────────────────────
LLM_PROVIDER=mock            # claude | openai | gemini | llama | mock
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=                # OpenAI-compatible local servers (llama.cpp, Ollama, vLLM)
LLM_API_KEY=

# ── Qdrant ─────────────────────────────────────────────
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=legal_corpus

# ── Database / Redis (leave unset → in-memory fallbacks) ──
DATABASE_URL=postgresql://legalai:legalai@localhost:5432/legalai
REDIS_URL=redis://localhost:6379/0

# ── Auth ───────────────────────────────────────────────
# IMPORTANT: set a long random value in production
JWT_SECRET=change-me-in-production-please-rotate-this-secret

# ── Rate limiting ──────────────────────────────────────
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60

# ── Auto ingestion ─────────────────────────────────────
AUTO_INGEST_WATCH_DIR=data/raw_documents
AUTO_INGEST_INTERVAL_SECONDS=60
AUTO_INGEST_ENABLED=true
```

> **Dev shortcut:** with `DATABASE_URL` unset the backend runs on in-memory repositories and an
> in-memory rate limiter, so you can exercise the full API without Postgres or Redis.

---

## ▶️ Running the Project

### Option A — Full Stack with Docker Compose (recommended)

```bash
docker compose up -d --build
```

| Service | URL |
|---|---|
| Web UI (Next.js) | http://localhost:3000 |
| FastAPI + Swagger | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/health |
| Qdrant Dashboard | http://localhost:6333/dashboard |
| PostgreSQL | localhost:5432 (legalai / legalai / legalai) |
| Redis | localhost:6379 |

### Option B — Local Development

```bash
# Terminal 1 — backend (http://localhost:8000)
source .venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2 — frontend (http://localhost:3000)
cd frontend
npm run dev

# Terminal 3 — infrastructure (Qdrant + Postgres + Redis)
docker compose up -d qdrant postgres redis
```

The Next.js dev server proxies `/api/*` to the backend, so no extra CORS config is needed.

### Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Create account (returns JWT + refresh token) |
| `POST` | `/api/auth/login` | Sign in |
| `POST` | `/api/auth/refresh` | Rotate the refresh token |
| `POST` | `/api/auth/logout` | End the current session |
| `GET` | `/api/auth/me` | Current user profile |
| `POST` | `/api/conversations/chat` | Chat with a conversation (non-streaming) |
| `POST` | `/api/conversations/chat/stream` | Chat with a streaming (NDJSON) response |
| `GET` | `/api/conversations` | List conversations (`?pinned=&search=&limit=`) |
| `GET` | `/api/conversations/{id}` | Conversation detail with messages |
| `GET` | `/api/conversations/{id}/export` | Markdown export |
| `POST` | `/api/conversations/{id}/share` | Create a public share link |
| `GET` | `/api/share/{slug}` | Public conversation view (no auth) |
| `POST` | `/api/query` | Stateless generation (retrieve + answer + verify) |
| `POST` | `/api/search` | Hybrid corpus search |
| `POST` | `/api/ingest` | Queue a directory ingestion job |
| `GET` | `/api/jobs` | List ingestion jobs |
| `GET` | `/api/admin/stats` | System stats (admin only) |
| `GET` | `/metrics` | Prometheus metrics |

### Quickstart Demo

```bash
# 1. register a user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"password123","full_name":"You"}'

# 2. ask a question (stateless, no auth required)
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the essential ingredients of murder under Section 300 IPC?"}'

# 3. queue an ingestion job
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"path": "data/raw_documents"}'
```

### Running Tests

```bash
# backend (from repo root, with venv active)
python -m pytest tests/ -q

# frontend
cd frontend
npm run typecheck
npm test
```

### Sample Response

```json
{
  "answer": "Under Section 300 IPC, murder requires an act done with the intention of causing death, or causing such bodily injury as is likely to cause death, except for the exceptions enumerated in the Section.",
  "confidence": 0.87,
  "claims": [
    {
      "text": "Murder requires intention to cause death.",
      "verdict": "SUPPORTED",
      "score": 0.93,
      "citations": [
        {
          "source": "Indian Penal Code, 1860",
          "section": "300",
          "page": 112,
          "chunk_id": "ipc-1860-300-0042"
        }
      ]
    }
  ],
  "sources": ["ipc-1860.pdf"],
  "warning": null
}
```

---

## 🚀 Future Scope

- **Multi-jurisdiction support** — pluggable jurisdiction packs (India, US, UK, EU).
- **Fine-tuned legal embedding models** — domain-adapted vectors via contrastive fine-tuning.
- **Graph-based legal reasoning** — connect statutes, precedents, and amendments in a legal knowledge graph (RAG + GNN).
- **Temporal law awareness** — track amendments and overruled precedents with versioned indexing.
- **Multilingual legal QA** — extend to Hindi, Tamil, and other regional legal languages.
- **Streaming + tool-use agents** — autonomous legal research agents that iterate retrieval.
- **Feedback loop** — user corrections fine-tune retrieval and confidence calibration over time.
- **Doc-level summarization & drafting** — contract review and clause drafting on the same evidence engine.
- **On-prem / air-gapped deployment** — fully local models for confidentiality-bound legal teams.

---

## 🧪 Research Contributions

1. **Summary-Augmented Chunking** — demonstrating that fusing parent-section summaries into chunk embeddings measurably reduces answer hallucination compared to naive fixed-size chunking.
2. **Legal Hybrid Retrieval Evaluation** — a comparative study of BM25-only, dense-only, and hybrid (RRF + cross-encoder) retrieval on a legal QA corpus.
3. **Citation-Verification-as-Safety-Layer** — an empirical analysis of post-generation entailment-based hallucination detection for legal domains.
4. **Confidence Calibration for Legal QA** — a method for producing trustworthy, calibrated confidence scores grounded in retrieval and verification signals.
5. **Open Benchmark** — a public golden legal QA dataset with ground-truth citations, enabling reproducible evaluation across systems.

*Target venue: IEEE — e.g., IEEE ICCCNT / ICMLA / ICTAI, or an NLP-specific workshop.*

---

## 💼 Startup Vision

**Product:** *Evidence-first AI copilots for law firms, legal departments, and legal-tech platforms.*

**The wedge:** every current legal AI product silently guesses. Our differentiator is the **verification layer** — answers that are traceable, citable, and confidence-scored. That is what lawyers are willing to pay for.

### Market Opportunity
- Legal-tech is a **multi-billion-dollar** market with accelerating AI adoption.
- Firms face pressure to cut research costs while managing hallucination risk — our system directly de-risks LLM usage.

### Product Roadmap
1. **MVP (this project)** → research Q&A for a single jurisdiction.
2. **Vertical SaaS** → jurisdiction packs + document analysis + drafting.
3. **Developer Platform** → API + SDKs so legal platforms embed verification.
4. **Compliance-Grade** → audit logs, SOC 2, and court-ready citation reports.

### Moats
- Proprietary **verification & calibration** pipeline.
- Curated **legal corpora** and evaluation benchmarks.
- **Domain-tuned models** from closed-loop lawyer feedback.

### Business Model
- SaaS subscriptions per seat.
- Usage-based API pricing.
- Enterprise contracts for air-gapped deployments.

---

## 📚 References

1. Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS. [arXiv:2005.11401](https://arxiv.org/abs/2005.11401)
2. Robertson, S., & Zaragoza, H. (2009). *The Probabilistic Relevance Framework: BM25 and Beyond.* Foundations and Trends in Information Retrieval.
3. Cormack, G., Clarke, C., & Buettcher, S. (2009). *Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods.* SIGIR.
4. Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.* EMNLP. [arXiv:1908.10084](https://arxiv.org/abs/1908.10084)
5. Gao, L., et al. (2021). *Condenser: a Pre-training Architecture for Dense Retrieval.* [arXiv:2104.08253](https://arxiv.org/abs/2104.08253)
6. Nogueira, R., & Cho, K. (2019). *Passage Re-ranking with BERT.* [arXiv:1901.04085](https://arxiv.org/abs/1901.04085)
7. Es, S., et al. (2024). *RAGAS: Automated Evaluation of Retrieval Augmented Generation.* EACL. [arXiv:2309.15217](https://arxiv.org/abs/2309.15217)
8. Huang, J., et al. (2024). *NLI-based Fact Verification & Hallucination Detection in RAG.* [arXiv:2305.10357](https://arxiv.org/abs/2305.10357)
9. Zhang, Y., et al. (2024). *Benchmarking Large Language Models in Retrieval-Augmented Generation.* AAAI. [arXiv:2309.01431](https://arxiv.org/abs/2309.01431)
10. Qdrant Documentation — *Hybrid Search & Payload Filtering.* https://qdrant.tech/documentation/
11. Johnson, J., Douze, M., & Jégou, H. (2019). *Billion-Scale Similarity Search with GPUs.* IEEE TPAMI. (HNSW foundations)
12. Malkov, Y., & Yashunin, D. (2020). *Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs.* IEEE TPAMI.
13. OpenAI. (2023). *GPT-4 Technical Report.* [arXiv:2303.08774](https://arxiv.org/abs/2303.08774)
14. Shuster, K., et al. (2021). *Retrieval Augmentation Reduces Hallucination in Conversation.* EMNLP. [arXiv:2104.07567](https://arxiv.org/abs/2104.07567)

---

<div align="center">

**Built as a College Mini Project · Submitted as an IEEE Research Paper · Showcased as a Portfolio Project · Engineered as a Startup Seed**

---

⭐ Star this repository if it helped you — and feel free to open issues for features, benchmarks, or collaboration.

</div>
# -hallucination-legal-ai
