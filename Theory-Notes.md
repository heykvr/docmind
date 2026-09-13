# Theory Notes — Day 1 & 2

Quick-review cheat sheet. Full narrative + bugs/fixes: see `Notes.md`.

## RAG Fundamentals
- **RAG** — retrieve relevant text from your own docs, feed it into the LLM prompt as context, instead of relying on the model's training memory. Fixes: private/recent data, reduces hallucination.
- **Why not just paste the whole doc in?** Context windows are limited/costly. Retrieval picks only the top-k relevant chunks.
- **Groundedness / faithfulness** — is the model's claim actually supported by the retrieved text, not just near it? (Day 1's bug: citation present, claim false.)

## Embeddings & Vector Search
- **Embedding** — text → a vector of numbers where similar meaning = nearby vectors.
- **Similarity metric** — cosine / L2 / dot product distance. Lower distance = more similar (pgvector's score).
- **Dense vs. sparse retrieval** — dense = embeddings/semantic (what we did). Sparse = keyword/BM25, exact-word match. Hybrid = both combined (coming Day 4-5).
- **ANN index (e.g. HNSW)** — how vector DBs find nearest neighbors fast without brute-force comparing every vector.
- **Collection** — a named, isolated set of vectors in the same store (`documents` vs `documents_v2`).

## Chunking Strategies
- **Fixed-size chunking** (Day 1) — split by raw char count + overlap. Simple, fast, structure-blind — can slice a table/sentence in half.
- **Chunk overlap** — repeat some chars between chunks so a boundary-split sentence still appears whole somewhere.
- **Semantic / structure-aware chunking** (Day 2) — chunk boundaries follow real document structure (headings, tables), not char count.
- **Core tradeoff** — too big = irrelevant text dilutes the match; too small = loses context (a number with no explanation). Isolating tables as their own chunk avoids both.

## Document Parsing & OCR
- **Text-layer extraction** — reading characters already stored in the PDF (`pypdf`). Fast, layout-blind.
- **Layout detection** — ML model reads the page *image*, classifies regions (title/paragraph/table/figure). Basis for `element.category`.
- **OCR** — recognizing text from a scanned image with no real text layer at all (a "photo of text," not stored characters).
- **Element/block classification** — breaking a doc into typed regions instead of one flat text blob. Foundation for both boilerplate filtering and semantic chunking.

## Metadata & Citations
- **Metadata** — structured facts attached to a chunk (`source`, `page_label`, `element_type`, `bbox`, `section_title`).
- **bbox** — pixel coordinates of an element on the page. Basis for future element/table-level citation (point at the exact region, not just the page).
- **page_label vs. physical page index** — printed page number (from PDF's `/PageLabels`) vs. raw zero-indexed file position. Easy off-by-one bug if ignored.

## Prompting & Generation
- **Prompt template** — fixed instructions + placeholders (`{context}`, `{question}`) filled per query.
- **Context stuffing** — concatenating retrieved chunks into one string inserted into the prompt.
- **Grounding instructions** ("answer ONLY from context, else say Not found") — guardrail against hallucination. Can backfire: over-refuses on questions needing implicit arithmetic.
- **Temperature** — randomness in generation. `0` = deterministic, most-likely output — right choice for fact-grounded answers.

## LangChain Abstractions
- **`Document`** — universal container: `page_content` + `metadata`. Everything (loaders, splitters, stores) speaks this.
- **Loader** — file → `Document`s (`PyPDFLoader`).
- **Text splitter** — big `Document` → smaller chunked `Document`s (`RecursiveCharacterTextSplitter`).
- **`Embeddings` interface** — standard `embed_query`/`embed_documents` methods any provider (Ollama, OpenAI, Cohere) implements.
- **`VectorStore` interface** — standard `add_documents`/`similarity_search_with_score` methods any vector DB implements — lets you swap stores without rewriting the pipeline.
