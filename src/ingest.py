from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader
from unstructured.partition.pdf import partition_pdf

from db import get_store

DATA_DIR = Path(__file__).parent.parent / "data"

BOILERPLATE_CATEGORIES = {"Header", "Footer", "PageBreak"}
BOILERPLATE_MARKERS = (
    "©",
    "some rights reserved",
    "all rights reserved",
    "rights and permissions",
    "creative commons attribution",
    "shall constitute or be construed",
    "international bank for reconstruction and development",
    "the world bank does not guarantee",
    "the boundaries, colors, denominations",
)
MAX_CHARS = 1000


def _page_labels(pdf_path: Path) -> list[str]:
    return PdfReader(str(pdf_path)).page_labels


def _is_boilerplate(el) -> bool:
    if el.category in BOILERPLATE_CATEGORIES:
        return True
    text = el.text.strip().lower()
    return any(m in text for m in BOILERPLATE_MARKERS)


def _bbox(el):
    coords = el.metadata.coordinates
    if not coords:
        return None
    xs = [float(p[0]) for p in coords.points]
    ys = [float(p[1]) for p in coords.points]
    return [min(xs), min(ys), max(xs), max(ys)]


def _partition(pdf_path: Path, strategy: str):
    return partition_pdf(str(pdf_path), strategy=strategy, infer_table_structure=True)


def chunk_elements(elements, page_labels, source_name):
    """Group filtered elements into chunks along Title boundaries, keeping
    Tables as their own chunk (element-level bbox stays precise for tables).
    """
    kept = [e for e in elements if e.text.strip() and not _is_boilerplate(e)]
    dropped = len(elements) - len(kept)

    chunks = []
    buf_text, buf_els, section_title = [], [], None

    def flush():
        if not buf_els:
            return
        page_no = buf_els[0].metadata.page_number
        chunks.append(
            Document(
                page_content="\n".join(buf_text),
                metadata={
                    "source": source_name,
                    "element_type": buf_els[0].category,
                    "page_label": page_labels[page_no - 1] if page_no else None,
                    "bbox": _bbox(buf_els[0]),
                    "section_title": section_title,
                },
            )
        )

    for el in kept:
        if el.category == "Title":
            flush()
            buf_text, buf_els = [], []
            section_title = el.text.strip()

        is_table = el.category == "Table"
        over_budget = sum(len(t) for t in buf_text) + len(el.text) > MAX_CHARS

        if buf_els and (is_table or over_budget):
            flush()
            buf_text, buf_els = [], []

        buf_text.append(el.text)
        buf_els.append(el)

        if is_table:
            flush()
            buf_text, buf_els = [], []

    flush()
    return chunks, len(elements), dropped


def load_and_chunk(strategy: str = "hi_res"):
    all_chunks = []
    for pdf in sorted(DATA_DIR.glob("*.pdf")):
        page_labels = _page_labels(pdf)
        elements = _partition(pdf, strategy)
        chunks, total, dropped = chunk_elements(elements, page_labels, pdf.name)
        print(f"{pdf.name}: {total} elements -> {dropped} dropped as boilerplate -> {len(chunks)} chunks")
        all_chunks.extend(chunks)
    return all_chunks


CACHE = Path(__file__).parent / "_chunks_cache.pkl"


if __name__ == "__main__":
    import pickle

    if CACHE.exists():
        docs = pickle.loads(CACHE.read_bytes())
        print(f"Loaded {len(docs)} cached chunks from {CACHE}")
    else:
        docs = load_and_chunk()
        CACHE.write_bytes(pickle.dumps(docs))
        print(f"Cached {len(docs)} chunks to {CACHE}")

    store = get_store("documents_v2")
    store.add_documents(docs)
    print(f"\nIndexed {len(docs)} chunks.")
    CACHE.unlink()

    print("\n--- sample chunk ---")
    print(docs[5].metadata)
    print(docs[5].page_content[:400])
