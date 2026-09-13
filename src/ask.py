import sys

from langchain_ollama import ChatOllama

from retrieve import search

PROMPT = """Answer the question using ONLY the context below.
If the context does not contain the answer, say "Not found in the documents."
Cite the source and page for each claim, like [report.pdf p.12].

Context:
{context}

Question: {question}
"""


def ask(question: str, collection: str = "documents"):
    hits = search(question, k=4, collection=collection)
    context = "\n\n".join(
        f"[{d.metadata.get('source')} p.{d.metadata.get('page_label', d.metadata.get('page'))}]\n{d.page_content}"
        for d, _ in hits
    )
    llm = ChatOllama(model="llama3.1", temperature=0)
    return llm.invoke(PROMPT.format(context=context, question=question)).content


if __name__ == "__main__":
    args = sys.argv[1:]
    collection = "documents"
    if args and args[0] in ("documents", "documents_v2"):
        collection, args = args[0], args[1:]
    query = " ".join(args) or "What was total revenue?"
    print(ask(query, collection=collection))