# Future work

These are planned improvements, not current product guarantees. Estimates are rough implementation estimates and exclude deployment and evaluation time.

| Improvement | Feasibility / estimate | Implementation and acceptance criteria |
|---|---|---|
| Cache summaries by document hash | High / 1–2 days | Compute SHA-256 over uploaded PDF bytes, or a defined UTF-8 representation for a future text flow. Before vector indexing, perform a parameterized documents lookup by `file_hash`. Reuse completed summaries/indexes only when the caller is authorized; share only explicitly public library artifacts across users. Include model, prompt, and pipeline versions in cache validity. Handle concurrent uploads and incomplete entries. Verify that identical content avoids re-indexing and changed content misses the cache. |
| Clause-level risk flags / unfair clause tagging | High / 2–3 days | Extend existing regex heuristics into fixed classifiers for Arbitration, Class Action Waiver, Unilateral Modification, Auto-Renewal, and Data Selling. Use a prompt with a validated JSON schema or evaluate a lightweight classifier head. Return evidence and source references with present/absent/unknown states. Evaluate negation, exceptions, and false positives. Category tags are not legal determinations of unfairness. |
| Long-context LLM baseline and cost comparison | High / 1–2 days | Send full agreement text directly to available long-context models. Original candidates: Gemini 1.5 Flash, Claude 3.5 Haiku, and Groq Llama 3.3; verify availability and use supported model IDs when running. Select one agreement per service for a four-agreement comparison, record filenames/hashes, and use identical questions for RAG and baseline. Log input/output tokens, extraction time, request and end-to-end latency, provider/model/date, retries, and cost using dated prices. Compare citation support, answer quality, and abstention too. Treat 1.5s, 75s, and $0.001 as hypotheses, not baseline measurements. Do not send private documents to hosted models without authorization. |
| URL-based ingestion / paste flow | High / 1 day | Add Next.js Paste URL and Paste Text inputs with matching backend routes. Reuse `api/utils/validation.py`, enforcing safety on redirects and the actual fetch, response size, timeout, and content types. Extract page text into the existing pipeline. Validate pasted-text size and preserve URL, retrieval date, and hash. Current API uploads accept PDFs only; importing the validator does not implement this flow. |

## Demo experience

- Build an explicitly public, versioned library of popular agreements with precomputed summaries and selected Q&A. Serve these first and label document versions. New questions/custom documents still need inference.
- Add example-question buttons and a guest path for public examples.
- Show backend wake-up, indexing, and generation progress, with estimates based on measurements. Assess the idle cost of a warm backend against first-visit latency.
- Record a GIF/video and add the real asset near the README demo link. Test signup, login, upload, a cited answer, and history from a fresh browser before sharing.
- Measure citation accuracy and correct abstentions on answerable/unanswerable inputs. Regenerate quality and latency artifacts together with a code revision and configuration manifest.
