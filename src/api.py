from fastapi import FastAPI
from pydantic import BaseModel

from ask import ask
from celery_app import app as celery_app
from storage import get_client, list_pdf_keys
from tasks import ingest_document

app = FastAPI(title="docmind")


class AskRequest(BaseModel):
    question: str
    collection: str = "documents_v2"


class IngestRequest(BaseModel):
    collection: str = "documents_v2"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def trigger_ingest(req: IngestRequest):
    client = get_client()
    keys = list_pdf_keys(client)

    tasks = []
    for key in keys:
        result = ingest_document(key, req.collection)
        tasks.append({"key": key, "task_id": result.id})

    return {"bucket_pdfs": keys, "enqueued": tasks}


@app.get("/ingest/{task_id}")
def ingest_status(task_id: str):
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "state": result.state,
        "result": result.result if result.ready() else None,
    }


@app.post("/ask")
def ask_question(req: AskRequest):
    answer = ask(req.question, collection=req.collection)
    return {"question": req.question, "collection": req.collection, "answer": answer}
