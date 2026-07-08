"""Vector Store using ChromaDB for semantic job search.
Embeds jobs and resumes using sentence-transformers.
"""
import os
from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


# === HF Spaces: Use /tmp (only writable directory) ===
CHROMA_PATH = Path(os.environ.get("CHROMA_PATH", "/tmp/chroma_db"))
CHROMA_PATH.mkdir(parents=True, exist_ok=True)

# Collection names
JOBS_COLLECTION = "jobs_collection"
RESUMES_COLLECTION = "resumes_collection"

# Embedding model (local, free)
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Singleton instances
_chroma_client: Optional[chromadb.PersistentClient] = None
_embedding_model: Optional[SentenceTransformer] = None


def get_chroma_client() -> chromadb.PersistentClient:
    """Get or create ChromaDB client (persistent)."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False
            )
        )
    return _chroma_client


def get_embedding_model() -> SentenceTransformer:
    """Get or load embedding model (singleton)."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def embed_text(text: str) -> List[float]:
    """Embed a single text into vector."""
    model = get_embedding_model()
    return model.encode(text, convert_to_tensor=False).tolist()


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed multiple texts into vectors (batched, faster)."""
    model = get_embedding_model()
    return model.encode(texts, convert_to_tensor=False).tolist()


class JobVectorStore:
    """Vector store for job postings with duplicate detection."""
    
    def __init__(self):
        self.client = get_chroma_client()
        self.collection = self.client.get_or_create_collection(
            name=JOBS_COLLECTION,
            metadata={"description": "Job postings for semantic search"}
        )
    
    def _get_existing_urls(self) -> set:
        """Get all existing job URLs from database."""
        try:
            all_jobs = self.collection.get()
            urls = set()
            for metadata in all_jobs.get("metadatas", []):
                if metadata and "url" in metadata:
                    urls.add(metadata["url"])
            return urls
        except Exception:
            return set()
    
    def _get_existing_ids(self) -> set:
        """Get all existing job IDs from database."""
        try:
            all_jobs = self.collection.get()
            return set(all_jobs.get("ids", []))
        except Exception:
            return set()
    
    def _make_job_id(self, job: Dict) -> str:
        """Generate unique ID for a job based on URL or title+company."""
        url = job.get("url") or job.get("link") or ""
        if url:
            return f"job_{hash(url) % 10**10}"
        
        title = job.get("title", "")
        company = job.get("company", "")
        return f"job_{hash(f'{title}_{company}') % 10**10}"
    
    def add_jobs(self, jobs: List[Dict]) -> Dict[str, int]:
        """Add jobs to vector store with duplicate detection."""
        if not jobs:
            return {"added": 0, "skipped": 0}
        
        existing_ids = self._get_existing_ids()
        
        documents = []
        metadatas = []
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
            
            doc_text = f"{title} at {company}. Location: {location}. {description} {snippet}"
            documents.append(doc_text)
            metadatas.append({
                "title": title,
                "company": company,
                "location": location,
                "url": url,
                "source": source,
            })
            ids.append(job_id)
        
        if documents:
            embeddings = embed_texts(documents)
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
        
        return {"added": len(documents), "skipped": skipped_count}
    
    def search_jobs(self, query: str, n_results: int = 10, filter_remote: Optional[bool] = None) -> List[Dict]:
        """Search jobs by semantic similarity."""
        if self.collection.count() == 0:
            return []
        
        query_embedding = embed_text(query)
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, self.collection.count()),
            )
        except Exception:
            return []
        
        jobs = []
        for i, (doc, metadata, distance) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            jobs.append({
                "title": metadata.get("title", ""),
                "company": metadata.get("company", ""),
                "location": metadata.get("location", ""),
                "url": metadata.get("url", ""),
                "source": metadata.get("source", ""),
                "description": doc,
                "semantic_score": float(distance),
                "match_score": max(0, 100 - float(distance) * 10),
            })
        
        return jobs
    
    def get_stats(self) -> Dict:
        """Get vector store statistics."""
        try:
            return {
                "total_jobs": self.collection.count(),
                "collection_name": self.collection.name,
                "chroma_path": str(CHROMA_PATH),
            }
        except Exception as e:
            return {"error": str(e)}


class ResumeVectorStore:
    """Vector store for user resumes."""
    
    def __init__(self):
        self.client = get_chroma_client()
        self.collection = self.client.get_or_create_collection(
            name=RESUMES_COLLECTION,
            metadata={"description": "User resumes for semantic search"}
        )
    
    def add_resume(self, user_id: int, resume_text: str, skills: List[str], roles: List[str]):
        """Add or update a user resume in vector store."""
        resume_id = f"resume_{user_id}"
        
        embedding = embed_text(resume_text)
        
        self.collection.upsert(
            ids=[resume_id],
            documents=[resume_text],
            embeddings=[embedding],
            metadatas=[{
                "user_id": user_id,
                "skills": ", ".join(skills),
                "roles": ", ".join(roles),
            }]
        )
    
    def get_resume(self, user_id: int) -> Optional[Dict]:
        """Get a user resume from vector store."""
        try:
            result = self.collection.get(ids=[f"resume_{user_id}"])
            if result["documents"]:
                return {
                    "text": result["documents"][0],
                    "skills": result["metadatas"][0].get("skills", "").split(", "),
                    "roles": result["metadatas"][0].get("roles", "").split(", "),
                }
        except Exception:
            pass
        return None