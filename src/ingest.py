from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from db import get_store

DATA_DIR = Path(__file__).parent.parent / "data"


def load_and_split():
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    all_chunks = []

    for pdf in sorted(DATA_DIR.glob("*.pdf")):
        pages = PyPDFLoader(str(pdf)).load()
        chunks = splitter.split_documents(pages)
        for chunk in chunks:
            chunk.metadata["source"] = pdf.name
        all_chunks.extend(chunks)
        print(f"{pdf.name}: {len(pages)} pages -> {len(chunks)} chunks")

    return all_chunks


if __name__ == "__main__":
    chunks = load_and_split()
    store = get_store()
    store.add_documents(chunks)
    print(f"\nIndexed {len(chunks)} chunks.")

    print("\n--- sample chunk ---")
    print(chunks[5].metadata)
    print(chunks[5].page_content[:400])