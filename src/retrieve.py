import sys

from db import get_store


def search(question: str, k: int = 4):
    store = get_store()
    return store.similarity_search_with_score(question, k=k)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "What was total revenue?"
    for doc, score in search(query):
        meta = doc.metadata
        print(f"\n[{meta.get('source')} p.{meta.get('page')}] score={score:.4f}")
        print(doc.page_content[:300].replace("\n", " "))