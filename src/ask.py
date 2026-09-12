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


def ask(question: str):
    hits = search(question, k=4)
    context = "\n\n".join(
        f"[{d.metadata.get('source')} p.{d.metadata.get('page')}]\n{d.page_content}"
        for d, _ in hits
    )
    llm = ChatOllama(model="llama3.1", temperature=0)
    return llm.invoke(PROMPT.format(context=context, question=question)).content


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "What was total revenue?"
    print(ask(query))