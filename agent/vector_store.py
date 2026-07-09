"""Vector Store using Qdrant for semantic job search.
Embeds jobs and resumes using sentence-transformers.
"""
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
)
from sentence_transformers import SentenceTransformer


# === Qdrant Cloud (via env vars) or local embedded fallback ===
QDRANT_PATH = Path(os.environ.get("QDRANT_PATH", "/tmp/qdrant_db"))
QDRANT_PATH.mkdir(parents=True, exist_ok=True)

QDRANT_URL = os.environ.get("QDRANT_URL")          # Qdrant Cloud cluster URL
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")  # Qdrant Cloud API key

# Collection names
JOBS_COLLECTION = "jobs_collection"
RESUMES_COLLECTION = "resumes_collection"

# Embedding model (local, free)
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Singleton instances
_qdrant_client: Optional[QdrantClient] = None
_embedding_model: Optional[SentenceTransformer] = None


def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client (Qdrant Cloud if configured, else local embedded mode)."""
    global _qdrant_client
    if _qdrant_client is None:
        if QDRANT_URL:
            _qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        else:
            _qdrant_client = QdrantClient(path=str(QDRANT_PATH))
    return _qdrant_client


def get_embedding_model() -> SentenceTransformer:
    """Get or load embedding model (singleton)."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def _get_vector_size(model: SentenceTransformer) -> int:
    """Get embedding dimension, compatible with old and new sentence-transformers versions."""
    if hasattr(model, "get_embedding_dimension"):
        return model.get_embedding_dimension()
    return model.get_sentence_embedding_dimension()


def embed_text(text: str) -> List[float]:
    """Embed a single text into a vector."""
    model = get_embedding_model()
    return model.encode(text, convert_to_tensor=False).tolist()


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed multiple texts into vectors (batched, faster)."""
    model = get_embedding_model()
    return model.encode(texts, convert_to_tensor=False).tolist()


def _ensure_collection(client: QdrantClient, name: str, vector_size: int):
    """Create the collection if it doesn't already exist."""
    try:
        client.get_collection(name)
    except Exception:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def _make_point_id(key: str) -> int:
    """Deterministically turn any string key into a valid Qdrant integer ID."""
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**63)


class JobVectorStore:
    """Vector store for job postings with duplicate detection."""

    def __init__(self):
        self.client = get_qdrant_client()
        self.collection_name = JOBS_COLLECTION
        vector_size = _get_vector_size(get_embedding_model())
        _ensure_collection(self.client, self.collection_name, vector_size)

    def _scroll_all(self):
        """Paginate through every point in the collection."""
        points = []
        offset = None
        while True:
            batch, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            points.extend(batch)
            if offset is None:
                break
        return points

    def _get_existing_ids(self) -> set:
        """Get all existing job point IDs from the database."""
        try:
            return {p.id for p in self._scroll_all()}
        except Exception:
            return set()

    def _make_job_id(self, job: Dict) -> int:
        """Generate a unique integer ID for a job based on URL or title+company."""
        url = job.get("url") or job.get("link") or ""
        if url:
            return _make_point_id(f"url:{url}")
        title = job.get("title", "")
        company = job.get("company", "")
        return _make_point_id(f"tc:{title}_{company}")

    def add_jobs(self, jobs: List[Dict]) -> Dict[str, int]:
        """Add jobs to vector store with duplicate detection."""
        if not jobs:
            return {"added": 0, "skipped": 0}

        existing_ids = self._get_existing_ids()

        doc_texts = []
        payloads = []
        ids = []
        skipped_count = 0

        for job in jobs:
            job_id = self._make_job_id(job)

            if job_id in existing_ids:
                skipped_count += 1
                continue

            title = job.get("title", "")
            company = job.get("company", "")
            location = job.get("location", "")
            description = job.get("description", "")
            snippet = job.get("snippet", "")
            url = job.get("url") or job.get("link", "")
            source = job.get("source", "unknown")
            remote = bool(job.get("remote", "remote" in location.lower()))

            doc_text = f"{title} at {company}. Location: {location}. {description} {snippet}"
            doc_texts.append(doc_text)
            payloads.append({
                "title": title,
                "company": company,
                "location": location,
                "url": url,
                "source": source,
                "remote": remote,
                "doc_text": doc_text,
            })
            ids.append(job_id)

        if doc_texts:
            embeddings = embed_texts(doc_texts)
            points = [
                PointStruct(id=ids[i], vector=embeddings[i], payload=payloads[i])
                for i in range(len(ids))
            ]
            self.client.upsert(collection_name=self.collection_name, points=points)

        return {"added": len(doc_texts), "skipped": skipped_count}

    def search_jobs(self, query: str, n_results: int = 10, filter_remote: Optional[bool] = None) -> List[Dict]:
        """Search jobs by semantic similarity."""
        if self.get_stats().get("total_jobs", 0) == 0:
            return []

        query_embedding = embed_text(query)

        qfilter = None
        if filter_remote is not None:
            qfilter = Filter(must=[FieldCondition(key="remote", match=MatchValue(value=filter_remote))])

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=qfilter,
                limit=n_results,
            )
        except Exception as e:
            print(f"QDRANT SEARCH ERROR: {e}")
            return []

        jobs = []
        for point in results:
            payload = point.payload or {}
            jobs.append({
                "title": payload.get("title", ""),
                "company": payload.get("company", ""),
                "location": payload.get("location", ""),
                "url": payload.get("url", ""),
                "source": payload.get("source", ""),
                "description": payload.get("doc_text", ""),
                "semantic_score": float(point.score),
                "match_score": round(max(0.0, min(100.0, point.score * 100)), 2),
            })

        return jobs

    def get_stats(self) -> Dict:
        """Get vector store statistics."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "total_jobs": info.points_count,
                "collection_name": self.collection_name,
                "qdrant_location": QDRANT_URL or str(QDRANT_PATH),
            }
        except Exception as e:
            return {"error": str(e)}


class ResumeVectorStore:
    """Vector store for user resumes."""

    def __init__(self):
        self.client = get_qdrant_client()
        self.collection_name = RESUMES_COLLECTION
        vector_size = _get_vector_size(get_embedding_model())
        _ensure_collection(self.client, self.collection_name, vector_size)

    def add_resume(self, user_id: int, resume_text: str, skills: List[str], roles: List[str] = None):
        """Add or update a user resume in vector store."""
        roles = roles or []
        embedding = embed_text(resume_text)

        point = PointStruct(
            id=int(user_id),
            vector=embedding,
            payload={
                "user_id": user_id,
                "text": resume_text,
                "skills": ", ".join(skills),
                "roles": ", ".join(roles),
            },
        )
        self.client.upsert(collection_name=self.collection_name, points=[point])

    def get_resume(self, user_id: int) -> Optional[Dict]:
        """Get a user resume from vector store."""
        try:
            records = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[int(user_id)],
                with_payload=True,
            )
            if records:
                payload = records[0].payload
                return {
                    "text": payload.get("text", ""),
                    "skills": payload.get("skills", "").split(", "),
                    "roles": payload.get("roles", "").split(", "),
                }
        except Exception:
            pass
        return None