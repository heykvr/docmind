import sys

from db import get_store


def search(question: str, k: int = 4, collection: str = "documents"):
    store = get_store(collection)
    return store.similarity_search_with_score(question, k=k)


if __name__ == "__main__":
    args = sys.argv[1:]
    collection = "documents"
    if args and args[0] in ("documents", "documents_v2"):
        collection, args = args[0], args[1:]
    query = " ".join(args) or "What was total revenue?"
    for doc, score in search(query, collection=collection):
        meta = doc.metadata
        page = meta.get("page_label", meta.get("page"))
        print(f"\n[{meta.get('source')} p.{page}] score={score:.4f}")
        print(doc.page_content[:300].replace("\n", " "))