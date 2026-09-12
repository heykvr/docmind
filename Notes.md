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