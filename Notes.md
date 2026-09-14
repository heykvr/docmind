## Day 1 baseline — 2026-09-12
Stack: PyPDFLoader → RecursiveCharacterTextSplitter(1000/200)
       → nomic-embed-text → pgvector → llama3.1
Corpus: 2 World Bank GEP reports, ~1900 chunks

Retrieval: surfaces relevant pages reliably (5/5 spot checks)

FAILURE — mis-grounded numbers:
Q: "By how much is global growth projected to slow in 2026?"
Model cited gep-jun-2026 p.40 for "1.1% → 0.7%".
Actual June GEP headline: 2.9% → 2.5%.
Numbers were real but belonged to a different series on the page.
Model then narrated a fake "discrepancy between reports."
→ Citations present but claim unsupported. This is what
  groundedness scoring (Day 6) has to catch.
The sample chunk is legal boilerplate. Copyright notices, rights and permissions, disclaimer text. It's now embedded and competing in every similarity search you run. Across 1,843 chunks you probably have 40–60 of these — front matter, back matter, page headers repeated on every page. They rarely win a search outright, but they consume slots in your top-k and add noise.

page is 5 but page_label is 6. PyPDFLoader's page is a zero-indexed PDF position; page_label is what's actually printed on the page. Your citations currently say "p.5" for a page the reader sees numbered 6. For a project whose selling point is exact citations, that's an off-by-one users would notice immediately. Worth switching to page_label in ask.py — and it's a nice detail to mention in an interview, because it shows you thought about the reader rather than the parser.

## Day 2 — Document Intelligence — 2026-09-13
Stack: unstructured.partition_pdf(strategy="hi_res") → Title-boundary
       semantic chunking (Table elements kept whole) → nomic-embed-text
       → pgvector (new collection: documents_v2) → llama3.1
Corpus: same 2 World Bank GEP reports, ingested side by side with the
        old `documents` collection (kept for comparison, not deleted).

Metadata schema per chunk: source, element_type, page_label, bbox,
section_title. bbox is captured now (from unstructured's element
coordinates) specifically so element/table-level citations are possible
later without a full re-ingest.

Boilerplate filtering (category = Header/Footer/PageBreak, plus a
legal-text keyword list): gep-jun-2026.pdf 4,399 elements → 527 dropped
(12%); gep-jan-2026.pdf 4,748 elements → 744 dropped (16%).
Chunk counts: gep-jun-2026.pdf 963 (Day 1) → 1,091 (Day 2),
gep-jan-2026.pdf → 977. Total documents_v2: 2,068 chunks.
Note: chunk count went UP, not down — not a sign filtering failed, just
that chunking granularity changed (Title-bounded + isolated Table
chunks vs. old fixed 1000/200-char slicing). The real boilerplate
signal is the element-level drop rate above.

page_label fix confirmed: citations now show the printed page number
(matches pypdf's PdfReader.page_labels), not PyPDFLoader's zero-indexed
position.

REGRESSION CHECK on Day 1's exact failing query
("By how much is global growth projected to slow in 2026?"):
Retrieval now surfaces the correct chunk — [gep-jun-2026.pdf p.27]:
"global growth is forecast to decelerate to 2.5 percent in 2026, down
from 2.9 percent in 2025" — cleanly, in the top-4, correctly page-
labeled. The Day 1 bug (real numbers grounded to the wrong series,
producing a fabricated "discrepancy between reports") is fixed.

NEW FINDING — over-conservative refusal on implicit arithmetic:
The literal Day 1 phrasing ("by how much...") still returns "Not found
in the documents," even though the answer chunk is in context. Cause:
answering requires computing 2.9 − 2.5 = 0.4, and the strict "use ONLY
the context" prompt makes llama3.1 decline rather than do arithmetic
not stated verbatim. Rephrasing to avoid requiring subtraction
("What is the global growth forecast for 2026 compared to 2025?")
answers correctly and cites [gep-jun-2026.pdf p.27]. This is a
different failure mode from Day 1's — worth its own eval case on
Day 6, separate from groundedness (call it "answerable-but-declines").

VALIDATION — genuine cross-report discrepancy handled correctly:
Q: "What is the global growth forecast for 2026?" (both PDFs in corpus)
→ "gep-jan-2026.pdf p.53: 2.6 percent... gep-jun-2026.pdf p.27: 2.5
percent... there seems to be a discrepancy between the two forecasts."
This is a REAL discrepancy (January's forecast was revised down by
June) and both citations/numbers are accurate — unlike Day 1, where the
model fabricated a discrepancy from mis-grounded numbers. Same surface
behavior (flagging a discrepancy) but now actually correct, because the
underlying retrieval is sound.

Ops notes: hi_res partitioning is CPU-heavy (~5-10 min per 200-page PDF
on this machine) and twice caused real instability during this session
— once crashing Docker Desktop's daemon entirely (containers stayed up
but the daemon socket vanished), and once crashing Ollama's Metal GPU
backend mid-embedding ("MTLCompilerService" error, fixed by restarting
`ollama serve`). ingest.py now caches parsed chunks to a local pickle
file before attempting the embed+store step, so a DB/embedding failure
doesn't require redoing the expensive parse.

Still open: S3 ingestion + Celery/Redis async processing (Day 3) —
scoped as part of Module 2 but deliberately deferred, not forgotten.

## Day 3 — Async Ingestion & API — 2026-09-14
Stack added: MinIO (S3-compatible, self-hosted — see reasoning below),
Celery + Redis (task queue), FastAPI (API surface). New files:
src/storage.py, src/celery_app.py, src/tasks.py, src/api.py.

CONTEXT SHIFT: this session surfaced that docmind isn't just a 10-day
learning exercise — it exists specifically to make two resume bullets
true and defensible (fully offline platform with LangChain/FastAPI/
Celery/Redis/Postgres+pgvector/Ollama; audit-ready answers via
layout-aware parsing, hybrid retrieval+reranking, LangGraph multi-step
agents, page-level citations, abstention on weak evidence, RAGAs in
CI). Reconciled three gaps against that: (1) FastAPI had zero footprint
in the codebase — pulled into Day 3 since it needed a trigger for async
ingestion anyway; (2) the original plan's "Cohere reranking" (Day 4-5)
is an external API call, which breaks "zero data leaving the network"
— swapped to a local cross-encoder reranker; (3) "LangGraph agents for
multi-step questions" wasn't in the roadmap at all — folded into Days
7-8 (Conversational RAG). Also: real AWS S3 was ruled out for the same
offline reason — MinIO (self-hosted, S3-compatible via boto3) used
instead.

ARCHITECTURE: two chained Celery tasks per document, not one monolithic
task — parse_task (download from MinIO, idempotency check, hi_res
parse+chunk) | embed_store_task (embed+write to Postgres). This
replaces yesterday's manual pickle-cache workaround with Celery's own
retry semantics: if embed_store_task fails and retries, only that step
re-runs — the 10-minute hi_res parse is NOT redone, because a chain's
upstream result is already resolved before the downstream task ever
retries.

BUG FOUND — macOS fork + native ML libs = SIGSEGV:
Celery's default "prefork" worker pool uses os.fork(). Forking a
process that has already loaded unstructured's ONNX layout model
crashes on macOS (signal 11) partway through parsing — reproduced
cleanly OUTSIDE Celery with the exact same PDF (worked fine standalone,
proving the PDF/library were not the problem). Fixed by running the
worker with `--pool=solo` (no forking, single process) instead of the
default prefork pool — also the correct choice anyway, since Day 2
already established hi_res shouldn't run with real parallelism on this
machine.

Ollama's Metal-compiler crash (same MTLCompilerService error as Day 2)
recurred again mid-session, this time surfaced through the FastAPI
/ask endpoint rather than a Celery task — meaning it's NOT covered by
the ingestion retry policy. Fixed the same way (restart `ollama serve`)
but this is a real gap: query-time embedding calls have no retry
protection yet. Not fixed today — flagged for whenever the FastAPI
layer gets hardened further.

MEASURED, not assumed — three real validations:
1. Idempotency: re-triggering /ingest against already-ingested PDFs
   completes in single-digit milliseconds (49ms, 8ms) vs. ~10 min for
   a real hi_res parse — proves the pre-parse DB check actually short-
   circuits, not just that it "should" in theory. Re-triggering a
   THIRD time after a document was freshly indexed confirmed exactly
   1 row for it in Postgres — no duplication from repeated triggers.
2. Full pipeline (not just skip-path): a fresh synthetic 1-page test
   PDF, uploaded to MinIO and ingested via POST /ingest, was correctly
   parsed (hi_res), chunked, embedded, stored, and retrievable via
   POST /ask with a correct, cited answer — proves the whole chain
   works end to end, not just the parts already proven in Day 2.
3. Retry resilience under a REAL outage, not a mocked one: stopped the
   Postgres container mid-task, on purpose. First attempt
   (max_retries=3, default backoff) FAILED permanently — retries
   exhausted in ~3-7s, faster than Postgres actually took to restart
   (~10s+). This is a real finding, not a test artifact: a retry policy
   that looks reasonable on paper can still be wrong for the actual
   failure duration it's meant to survive. Retuned to max_retries=8,
   retry_backoff_max=60s, re-ran the identical test (stop Postgres,
   wait a realistic ~8s, restart it) — task automatically recovered
   and succeeded with zero manual intervention, unlike Day 2's failures
   which required a human (me) to notice and manually restart/rerun.

API surface added (src/api.py): GET /health, POST /ingest (scans the
MinIO bucket, enqueues a parse|embed chain per PDF, returns
immediately), GET /ingest/{task_id} (poll status), POST /ask (wraps
the existing ask() — first time "query in natural language" is
reachable via an API, not only a CLI script).

Cleanup: removed synthetic test_doc.pdf/test_doc2.pdf chunks from
documents_v2 and their objects from MinIO after validation — they were
throwaway test fixtures, not real corpus content.

Repo hygiene fix: unstructured[pdf] was installed in Day 2 but never
added to requirements.txt (same class of bug as Day 1's missing
langchain_ollama) — fixed. Also added boto3, celery[redis], fastapi,
uvicorn[standard].

Still open: reranker swap to local cross-encoder (Day 4-5), abstention-
on-weak-evidence design (not concretely scoped to a day yet), removing
the unused OpenAI key/langchain-openai dependency (repo-hygiene, not
urgent), query-time Ollama retry protection (gap found today).