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