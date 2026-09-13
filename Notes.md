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