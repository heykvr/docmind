import os
import psycopg
from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings
from langchain_postgres import PGVector
load_dotenv()

COLLECTION = "documents"
DB_URL = os.environ["DB_URL"]
PSYCOPG_DSN = DB_URL.replace("postgresql+psycopg://", "postgresql://")

def get_store(collection: str = COLLECTION) -> PGVector:
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    return PGVector(
        embeddings=embeddings,
        collection_name=collection,
        connection=DB_URL,
        use_jsonb=True,
    )


def already_ingested(collection: str, source: str) -> bool:
    with psycopg.connect(PSYCOPG_DSN) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = %s AND e.cmetadata->>'source' = %s
            LIMIT 1
            """,
            (collection, source),
        )
        return cur.fetchone() is not None