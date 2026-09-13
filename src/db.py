import os
from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings
from langchain_postgres import PGVector
load_dotenv()

COLLECTION = "documents"
DB_URL = os.environ["DB_URL"]

def get_store(collection: str = COLLECTION) -> PGVector:
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    return PGVector(
        embeddings=embeddings,
        collection_name=collection,
        connection=DB_URL,
        use_jsonb=True,
    )