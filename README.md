# ClauseLens

Clause-grounded Q&A over terms of service, with cited answers, an abstention path, and CPU-only inference support.

**[Try the demo](https://tos-summarization.vercel.app)** · [Recording guide](DEMO.md) · [Future work](FUTURE_WORK.md) · [Deployment](DEPLOYMENT.md)

Nobody reads terms of service. ClauseLens helps you find and understand what they say about account sharing, cancellation, and content ownership. It retrieves supporting clauses and generates answers with source references. If it cannot extract sufficient evidence, it responds: “I do not have enough information to answer this.”

The engineering constraint is local inference with a quantized 7B model. A desktop backend mode uses local inference, ChromaDB, SQLite, and local file storage. The hosted demo uses cloud services. A shared precomputed library for popular services is **planned**; current questions still require inference.

> **Disclaimer:** This prototype can produce incomplete or incorrect answers. Check the cited clauses. It helps you find and understand document text and does not provide legal advice.

## Try it

Open the demo, sign in, and upload the bundled [Netflix agreement](data/TOS%20files/Netflix%20_%20Terms%20%26%20Conditions.pdf). After processing, try:

- “Am I allowed to share my Netflix account with people outside my household?”
- “What is Netflix's policy on refunds and cancellations?”
- “What is the capital of France?” — an out-of-scope abstention example from the recorded safety evaluation.

Inspect the source excerpts alongside the answers. These are suggested inputs, not preloaded answers. The hosted backend can take several minutes to wake up and about a minute per question. See [DEMO.md](DEMO.md) for a recording sequence and known answer issues. A demo GIF/video remains future work.

## What's interesting technically

- **Clause-grounded retrieval:** Dense search and BM25 are fused with reciprocal rank fusion, then reranked with a cross-encoder. Page and section metadata accompany source excerpts.
- **Evidence before synthesis:** One pass extracts evidence; another writes short answers with `[SOURCE N]` references. Insufficient evidence triggers abstention. This reduces unsupported generation but does not guarantee correctness.
- **CPU-capable inference:** Legal-Qwen, a legal-task fine-tuned Qwen 2.5 7B model, runs as `legal_qwen.Q4_K_M.gguf` through `llama-cpp-python`. Set `N_GPU_LAYERS=0` to force CPU inference.
- **End-to-end engineering:** Next.js 16 / React 19 frontend, FastAPI streaming responses, authentication, background ingestion, persisted history, structured logging, and deployment smoke checks.

## Tradeoffs and decisions

**Why a local 7B model?** Quantization makes inference feasible without a hosted generation API or dedicated GPU. The cost is slower answers and weaker handling of ambiguous clauses and exceptions. The desktop backend supports local execution; a packaged, fully offline frontend experience has not been established here.

**Why RAG?** Retrieval provides inspectable excerpts within the model's 8,192-token context window. Structure-aware chunking uses 1,200 characters with 300-character overlap, which can split related clauses. A full-document baseline is planned to test whether retrieval complexity pays off for short agreements.

**Why scale to zero?** The documented Cloud Run deployment uses `min-instances=0` to reduce idle hosting cost. Historical observations were roughly 4m 45s for a cold start, 66s for indexing, and 75s per question. These are not current service guarantees. Precomputed public examples and hash-based reuse are planned to improve first-visit latency.

**What exists for risk tagging?** Summary generation already invokes a deterministic regex-based classifier. These are experimental heuristic labels, not validated findings that a clause is unfair. Fixed, evidence-backed clause classifiers and their evaluation remain future work.

## Evaluation results

Checked-in quality artifacts cover **15 questions across 5 PDFs from 4 services**: Netflix, Spotify, YouTube, and OpenAI. The quality scripts use Groq's `llama-3.3-70b-versatile` as an LLM judge. These small offline runs are diagnostics, not a production accuracy claim or a measurement of the current demo.

| Metric | Recorded result | Artifact |
|---|---|---|
| Context recall | Approximately 0.93 | [Retrieval results](context_recall_results.csv) |
| Mean Q&A faithfulness | Approximately 0.88 | [Faithfulness results](faithfulness_summary.csv) |
| Mean answer relevance | 0.60 | [Relevance results](answer_relevance_results.csv) |
| Observed abstentions | 4/15 (27%) in the relevance run | [Relevance results](answer_relevance_results.csv) |
| Safety cases marked safe | 9/9, including out-of-scope and legal-advice prompts | [Safety results](red_team_results.csv) |
| Local Q&A latency, mean / median / P95 | 17.2s / 17.5s / 25.6s | [Latency summary](latency_summary.csv) |
| Local ingestion / global summary, mean | 1.9s / 67.1s | [Latency summary](latency_summary.csv) |

Latency comes from the Windows local benchmark dated June 4, 2026. Its CSV retains a legacy `faiss` metric name; the current desktop engine uses ChromaDB. Quality artifacts contain different answers for some identical questions and should be read as separate runs. Faithfulness includes abstentions with no factual claims, which can raise the average. **Citation accuracy and correct-abstention rate have not been separately measured.** Some recorded answers include unsupported or contradictory claims.

## Architecture

```text
Next.js -> FastAPI -> PDF extraction and structure-aware chunking
                  -> dense + BM25 retrieval -> reranking
                  -> evidence extraction -> cited answer / abstention
```

| Component | Server mode | Desktop backend mode |
|---|---|---|
| Generation | GGUF inference in backend container | Local GGUF inference |
| Vector storage | Pinecone | ChromaDB |
| Document/conversation records | Neon Postgres | SQLite |
| File storage | S3 archival | Local filesystem |
| Authentication | Neon Auth integration | Local-user bypass |

The backend includes upload MIME/size checks, URL-validation utilities, request logging, rate limiting, and ingestion retries. URL validation alone does not implement URL ingestion. Cloud Build deploys a candidate revision and runs smoke checks before moving traffic. See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment configuration and historical operational notes.

## Local setup

Use Python 3.11. Provision the GGUF at `models/legal_qwen.Q4_K_M.gguf`, embeddings at `models/embeddings`, and reranker assets at `models/cross-encoder/ms-marco-MiniLM-L-6-v2`. Installing dependencies does not provision these model assets.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r api/requirements.prod.txt
$env:RUNTIME_MODE = "desktop"
$env:N_GPU_LAYERS = "0"
uvicorn api.main:app --reload --host 127.0.0.1 --port 8080
```

On macOS/Linux, activate with `source .venv/bin/activate` and set `export RUNTIME_MODE=desktop N_GPU_LAYERS=0`. Native dependencies such as `llama-cpp-python` and `python-magic` may require system libraries.

Start the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend has separate API/auth configuration; see [frontend/README.md](frontend/README.md). Desktop mode describes the backend, not a verified offline frontend experience. Before using private documents, provision models locally, review tracing/logging settings including LangSmith, and verify that your complete setup makes no external calls.

For server mode, configure database, auth, vector storage, and storage settings in [api/core/config.py](api/core/config.py), following [DEPLOYMENT.md](DEPLOYMENT.md). Do not commit credentials.

Offline evaluation commands, after provisioning models and judge credentials:

```bash
python src/Evaluation/context_recall.py
python src/Evaluation/faithfulness.py
python src/Evaluation/answer_relevance.py
python src/Evaluation/red_team.py
python src/Evaluation/benchmark_latency.py
```

## Limitations

- The quantized model can miss evidence, misread exceptions, or produce incorrect answers despite citations. Retrieval success does not guarantee correctness.
- Abstention can occur even when the document contains an answer. The observed rate does not measure whether abstaining was correct.
- Hosted cold starts and CPU inference are slow. There is no shared instant-answer library or document-hash reuse yet.
- Risk labels use unvalidated rules and can mishandle negation or missing evidence. A low label does not establish safety.
- API uploads currently accept PDFs. URL and paste-text flows are planned.
- Bundled policies are snapshots and can differ from current terms or regional versions. This is not legal advice.

## Future work

See [FUTURE_WORK.md](FUTURE_WORK.md) for hash caching, fixed clause classifiers, long-context cost comparisons, URL/paste ingestion, and the precomputed demo library.

## Project description and resume wording

**Repository description:** ClauseLens answers questions about terms of service with source citations, an abstention path, and CPU-only inference support.

**Resume bullet:** Built an end-to-end terms-of-service Q&A prototype with Next.js, FastAPI, hybrid retrieval, and quantized 7B inference; evaluated 15 questions across 5 PDFs, with 17.2s mean local Q&A latency in the recorded benchmark.

**30-second pitch:** “Most people accept terms without reading them. I built ClauseLens to answer questions and show the supporting clauses. CPU inference forced tradeoffs in model size, retrieval, and latency. I built the frontend, backend, auth integration, deployment pipeline, and evaluation scripts. Next is a precomputed public-document library to improve the first-visit experience.”
