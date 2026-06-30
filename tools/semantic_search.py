# tools/semantic_search.py
import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
client = chromadb.PersistentClient(path="data/chroma")


def index_jobs(jobs):
    """Store jobs in vector DB for semantic search."""
    collection = client.get_or_create_collection("jobs")

    for i, job in enumerate(jobs):
        text = f"{job.get('title')} {job.get('company')} {job.get('snippet')}"
        embedding = model.encode(text).tolist()

        collection.add(
            ids=[str(i)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{"title": job.get("title"), "url": job.get("url")}]
        )


def semantic_search(query, n=10):
    """Find semantically similar jobs."""
    collection = client.get_collection("jobs")
    embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[embedding],
        n_results=n
    )
    return results