from pathlib import Path

from langchain_core.documents import Document
from ollama import ResponseError
from psycopg import OperationalError

from celery_app import app
from db import already_ingested, get_store
from ingest import _page_labels, _partition, chunk_elements
from storage import download_to_temp, get_client


@app.task(
    bind=True,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_kwargs={"max_retries": 8},
)
def parse_task(self, key: str, collection: str = "documents_v2"):
    source_name = Path(key).name

    if already_ingested(collection, source_name):
        print(f"{source_name}: already in '{collection}', skipping parse")
        return {"skipped": True, "source": source_name}

    client = get_client()
    local_path = download_to_temp(client, key)

    page_labels = _page_labels(local_path)
    elements = _partition(local_path, "hi_res")
    chunks, total, dropped = chunk_elements(elements, page_labels, source_name)
    print(f"{source_name}: {total} elements -> {dropped} dropped -> {len(chunks)} chunks")

    return {
        "skipped": False,
        "source": source_name,
        "chunks": [{"page_content": c.page_content, "metadata": c.metadata} for c in chunks],
    }


@app.task(
    bind=True,
    autoretry_for=(OperationalError, ResponseError),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_kwargs={"max_retries": 8},
)
def embed_store_task(self, parsed: dict, collection: str = "documents_v2"):
    if parsed["skipped"]:
        return {"source": parsed["source"], "indexed": 0, "skipped": True}

    docs = [Document(page_content=c["page_content"], metadata=c["metadata"]) for c in parsed["chunks"]]
    store = get_store(collection)
    store.add_documents(docs)
    print(f"{parsed['source']}: indexed {len(docs)} chunks into '{collection}'")

    return {"source": parsed["source"], "indexed": len(docs), "skipped": False}


def ingest_document(key: str, collection: str = "documents_v2"):
    return (parse_task.s(key, collection) | embed_store_task.s(collection)).apply_async()
