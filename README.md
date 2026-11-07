# TOS Summarizer

An end-to-end AI engineering prototype for legal document analysis, built as an architectural showcase.

Designed to demonstrate: **Advanced RAG Pipelines**, **Secure API Design**, and **Cloud-Native Deployment**.

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js-black)](https://nextjs.org/)
[![Cloud Run](https://img.shields.io/badge/Deploy-Google%20Cloud%20Run-4285F4)](https://cloud.google.com/run)
[![Vercel](https://img.shields.io/badge/Frontend-Vercel-000000)](https://vercel.com/)
[![Neon](https://img.shields.io/badge/Database-Neon%20Postgres-00E599)](https://neon.tech/)

> **Disclaimer:** This project is a technical prototype and architectural showcase only. It does not provide legal advice.

---

## What This Project Demonstrates

Built with production-style engineering practices, highlighting trade-offs and techniques relevant to legal document analysis:

- **Grounded Q&A & Document Extraction:** Hybrid retrieval (Dense Vector + BM25 with Reciprocal Rank Fusion) and cross-encoder reranking.
- **Production-Style Backend Engineering:** Structured JSON logging with request tracing, SlowAPI rate limiting, and dual deployment modes (`server` vs `desktop`).
- **Security-Minded Ingestion:** SSRF-safe URL validation (RFC-1918/link-local blocking) and MIME/size upload validation.
- **Serverless Cloud Run Pipeline:** Tagged revisions (`--no-traffic`), automated smoke testing, and traffic gating via Cloud Build.
- **Relational Backend & Managed Auth:** Neon Serverless PostgreSQL with connection pooling and Next.js / FastAPI integration.

---

## Live Deployment

- **Frontend:** https://tos-summarization.vercel.app
- **Backend:** https://tos-api-110277869308.us-east1.run.app

### Performance Benchmarks

#### Local Benchmark (CPU, `RUNTIME_MODE=desktop`)

Measured with `python src/Evaluation/benchmark_latency.py` on 5 PDFs and 15 questions from `data/Test_data.csv` (FAISS + GGUF on local CPU). Aggregates from `latency_summary.csv`.

| Stage | Latency | Notes |
|-------|---------|-------|
| Model load (one-time) | 18.0s | GGUF 2.5s, embeddings 0.2s, cross-encoder 0.1s |
| Document ingestion (avg) | 1.9s | PDF parse ~0.2s, FAISS index ~1.7s |
| Global summary (avg) | 1m 07s | ~9.6 tok/s on local CPU |
| Q&A per question (avg / median / P95) | 17.2s / 17.5s / 25.6s | Retrieval 1.3s, LLM 15.8s (~5.4 tok/s) |
| Full benchmark (5 docs + 15 Q&A) | 10m 21s | Batch local run |

#### Cloud Run (Serverless Portfolio Deployment)

Deployed on Cloud Run CPU with `min-instances=0` to keep hosting costs near zero.

| Operation | Latency | Tradeoff & Architectural Cause |
|-----------|---------|--------------------------------|
| Cold start | ~4m 45s | Serverless cold start: container boot + dynamic GCS Fuse volume mount of weights |
| Document indexing | ~1m 06s | PDF extraction, chunking, embedding generation & remote vector index upsert |
| Q&A (per question) | ~1m 15s | 4 vCPU unaccelerated GGUF inference (`llama-cpp-python`) |
| Summary (per topic) | ~1m 30s | Multi-topic extraction and synthesis on CPU |

> **Cost vs. Latency Tradeoff:** Cold starts and 75s inference times are deliberate design trade-offs of a low-cost portfolio deployment (`min-instances=0`, CPU-only). In a commercial setting, keeping `min-instances=1` with image-baked weights drops cold starts to ~30s; alternatively, offloading synthesis to a hosted LLM API (e.g. Claude 3.5 Haiku, Groq Llama 3.3, or Gemini Flash) achieves sub-2s responses at cents per thousand queries. See [DEPLOYMENT.md](./DEPLOYMENT.md) for full cost analysis.

---

## Architecture & System Design

### Core Inference Pipeline (`src/RAG/engine.py`)

- **Underlying Model:** **Legal-Qwen (Qwen 2.5 7B fine-tuned for legal tasks, quantized to `legal_qwen.Q4_K_M.gguf`)** executing via `llama-cpp-python`.
- **Embeddings & Reranker:** HuggingFace `sentence-transformers` embeddings (768-dim) and `cross-encoder/ms-marco-MiniLM-L-6-v2` (reranking top-50 candidates down to top-5/7).
- **Structure-Aware Chunking:** PyMuPDF extraction with page boundary markers (`<!-- page:N -->`), markdown header splitting, and recursive text chunking (1200 chars / 300 overlap) preserving `page`, `section`, and `citation` metadata.
- **Hybrid Retrieval:** Dense vector retrieval (Pinecone in server mode, ChromaDB in desktop mode) fused with BM25 keyword matching via **Reciprocal Rank Fusion (RRF)**, combined with legal query expansion (`src/RAG/query_expansion.py`).
- **Two-Stage Generation:**
  1. *Extract phase:* Pulls exact evidentiary sentences from context chunks or outputs `NONE`.
  2. *Synthesize phase:* Formulates concise answers strictly mapped to evidence with explicit `[SOURCE N]` tags.
- **Guardrails & Safety Refusals:** Deterministic checks for legal advice requests ("should I sue", "how to win in court"), routing them to an attorney referral disclaimer.

### Platform Components

- **Backend:** FastAPI with modular routers (`ingest`, `chat`, `history`, `auth`, `admin`).
- **Database:** **Neon Serverless Postgres** via connection pooling (`psycopg2.pool.ThreadedConnectionPool`) in server mode; SQLite (WAL mode) in desktop mode.
- **Authentication:** Dual support for **Neon Auth** (Managed Better Auth / JWT) and local developer tokens.
- **Vector Store:** Pinecone (serverless index) / ChromaDB (local persistence).
- **Object Storage:** AWS S3 for document archival / local file system in desktop mode.
- **CI/CD & Cloud:** Google Cloud Build, Artifact Registry, Google Cloud Run with GCS model weight mount.

---

## RAG Evaluation & Known Limitations

Offline evaluations are executed via `src/Evaluation/` against curated test data (`data/Test_data.csv` covering Netflix, Spotify, YouTube, and OpenAI policies):

| Metric | Score | Evaluation Target | Source CSV |
|--------|-------|-------------------|------------|
| **Context recall** | **0.93** (14/15; 2 partial) | Retrieval finds ground-truth clauses | `context_recall_results.csv` |
| **Faithfulness** | **0.88** (QA mode, 15 questions) | Synthesized claims backed by context | `faithfulness_summary.csv` |
| **Answer relevance** | **0.60** (4/15 abstentions) | Direct relevance of generated response | `answer_relevance_results.csv` |
| **Red team safety** | **100%** (9/9 safe) | Refusal of legal advice prompts | `red_team_results.csv` |

*Evaluated with Groq LLM-as-judge (`llama-3.3-70b-versatile`).*

### Critical Findings & Limitations

1. **Abstention Rate Analysis:**
   - 4 out of 15 questions (~27%) yielded abstentions ("I do not have enough information to answer this").
   - *Cause:* While context recall was high (0.93), the strict two-stage extraction prompt requires verbatim matches; when small 7B quantized models encounter ambiguous cross-references across chunks, the extractor outputs `NONE`. While this preserves **faithfulness** (no hallucinated terms), it penalizes **answer relevance**.
2. **Chunking & Legal Structure:**
   - Standard 1200-character chunking can fracture multi-clause dependencies (e.g., "Subject to Section 14, disputes shall be arbitrated...").
3. **Context vs. Full-Document Baseline:**
   - Most modern Terms of Service documents range between 5,000 and 20,000 words. Frontier models with 128k–1M context windows can consume entire agreements without chunking. RAG was selected here specifically to enable **offline local CPU execution** on consumer hardware and low-resource serverless tiers where memory is restricted to <8GB.
4. **Prior Art & Domain Comparison:**
   - This project focuses on technical RAG architecture. In production legal-tech, systems like **ToS;DR** (crowdsourced rights ratings) and academic benchmarks like **CLAUDETTE / UNFAIR-ToS** categorize specific unfair clauses (liability limits, unilateral changes, arbitration waivers). Adding structured clause classification is a planned extension.

---

## Engineering Highlights

- **Deployment Safety & Traffic Gating:** Cloud Build deploys candidate revisions with `--no-traffic --tag candidate`. A custom smoke-test script validates the revision endpoint before traffic is migrated. If the smoke test fails, the build halts and traffic remains on the prior working revision.
- **SSRF Mitigation:** `api/utils/validation.py` inspects target URLs, resolving DNS and blocking private/link-local IP addresses (RFC-1918, RFC-3927) and cloud metadata addresses (`169.254.169.254`).
- **Desktop/Server Abstraction:** Switching `RUNTIME_MODE=desktop` seamlessly redirects vector queries to ChromaDB and relational records to SQLite, enabling zero-cloud local testing.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11, TypeScript |
| Backend | FastAPI, Pydantic, Uvicorn, SlowAPI |
| LLM & Embeddings | `Legal-Qwen` (GGUF via llama-cpp-python), sentence-transformers, MiniLM CrossEncoder |
| Retrieval | LangChain, Pinecone, BM25, Reciprocal Rank Fusion |
| Database | Neon Serverless Postgres (production) / SQLite WAL (desktop) |
| Auth | Neon Auth (Managed Better Auth / JWT) |
| File Storage | AWS S3 / Local storage |
| Frontend | Next.js 16 (App Router), React 19, Lucide Icons |
| Cloud Infrastructure | Google Cloud Run, Artifact Registry, Google Cloud Storage, Vercel |

---

## Local Setup

### Backend

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r api/requirements.prod.txt
uvicorn api.main:app --reload --host 127.0.0.1 --port 8080
```

For desktop mode (no cloud dependencies):
```bash
RUNTIME_MODE=desktop uvicorn api.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run build
npm run dev
```

### Environment Variables (.env)
```env
DATABASE_URL=postgresql://...
DATABASE_URL_UNPOOLED=postgresql://...
NEON_AUTH_BASE_URL=https://...
NEON_AUTH_JWKS_URL=https://...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET_NAME=...
ADMIN_SECRET=...
ALLOWED_ORIGINS=http://localhost:3000
```

---

## Evaluation Commands

```bash
python src/Evaluation/context_recall.py
python src/Evaluation/faithfulness.py          # --mode qa | summary | both
python src/Evaluation/answer_relevance.py
python src/Evaluation/red_team.py
python src/Evaluation/benchmark_latency.py     # latency_summary.csv
```