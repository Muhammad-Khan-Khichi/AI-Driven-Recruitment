"""
Vector Store using ChromaDB for semantic job search.
Embeds jobs and resumes using sentence-transformers.
"""
import os
from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


# Persistent storage path
CHROMA_PATH = Path(__file__).parent.parent / "chroma_data"
CHROMA_PATH.mkdir(exist_ok=True)

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
    """Vector store for job postings."""
    
    def __init__(self):
        self.client = get_chroma_client()
        self.collection = self.client.get_or_create_collection(
            name=JOBS_COLLECTION,
            metadata={"description": "Job postings for semantic search"}
        )
    
    def add_jobs(self, jobs: List[Dict]) -> int:
        """
        Add jobs to vector store.
        Each job dict: {id, title, company, description, location, ...}
        """
        if not jobs:
            return 0
        
        # Prepare documents (what gets embedded)
        documents = []
        metadatas = []
        ids = []
        
        for job in jobs:
            # Create rich text representation for embedding
            doc_text = self._job_to_text(job)
            documents.append(doc_text)
            
            # Metadata for filtering
            metadata = {
                "title": str(job.get("title", "")),
                "company": str(job.get("company", "")),
                "location": str(job.get("location", "")),
                "source": str(job.get("source", "")),
                "url": str(job.get("url", "")),
                "remote": bool(job.get("remote", False)),
            }
            
            # Add salary if available
            if job.get("salary_min"):
                metadata["salary_min"] = float(job["salary_min"])
            if job.get("salary_max"):
                metadata["salary_max"] = float(job["salary_max"])
            
            metadatas.append(metadata)
            
            # Use job ID (or generate one)
            job_id = str(job.get("id") or f"job_{hash(doc_text) % 10**8}")
            ids.append(job_id)
        
        # Embed and add in batch
        embeddings = embed_texts(documents)
        
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        return len(jobs)
    
    def search_jobs(
        self,
        query: str,
        n_results: int = 10,
        filter_remote: Optional[bool] = None,
        min_salary: Optional[float] = None
    ) -> List[Dict]:
        """
        Semantic search for jobs matching query.
        Returns ranked list with similarity scores.
        """
        # Build where filter
        where_filter = {}
        if filter_remote is not None:
            where_filter["remote"] = filter_remote
        
        # Query
        query_embedding = embed_text(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter if where_filter else None
        )
        
        # Format results
        jobs = []
        if results["ids"] and results["ids"][0]:
            for i, job_id in enumerate(results["ids"][0]):
                # Calculate similarity (distance → similarity)
                distance = results["distances"][0][i] if "distances" in results else 0
                similarity = 1 - distance  # Convert distance to similarity
                
                jobs.append({
                    "id": job_id,
                    "title": results["metadatas"][0][i].get("title", ""),
                    "company": results["metadatas"][0][i].get("company", ""),
                    "location": results["metadatas"][0][i].get("location", ""),
                    "source": results["metadatas"][0][i].get("source", ""),
                    "url": results["metadatas"][0][i].get("url", ""),
                    "remote": results["metadatas"][0][i].get("remote", False),
                    "similarity_score": round(similarity, 3),
                    "document": results["documents"][0][i] if "documents" in results else ""
                })
        
        # Optional: filter by salary
        if min_salary is not None:
            filtered = []
            for job in jobs:
                # Get metadata salary (we'd need to fetch it separately)
                # For now, skip this filter
                filtered.append(job)
            jobs = filtered
        
        return jobs
    
    def get_stats(self) -> Dict:
        """Get vector store statistics."""
        count = self.collection.count()
        return {
            "total_jobs": count,
            "collection_name": JOBS_COLLECTION,
            "embedding_model": EMBEDDING_MODEL_NAME
        }
    
    def clear(self):
        """Clear all jobs (use carefully!)."""
        self.client.delete_collection(JOBS_COLLECTION)
        self.collection = self.client.get_or_create_collection(
            name=JOBS_COLLECTION,
            metadata={"description": "Job postings for semantic search"}
        )
    
    @staticmethod
    def _job_to_text(job: Dict) -> str:
        """Convert job dict to rich text for embedding."""
        parts = []
        if job.get("title"):
            parts.append(f"Job Title: {job['title']}")
        if job.get("company"):
            parts.append(f"Company: {job['company']}")
        if job.get("location"):
            parts.append(f"Location: {job['location']}")
        if job.get("description"):
            parts.append(f"Description: {job['description']}")
        if job.get("skills"):
            parts.append(f"Skills: {', '.join(job['skills'])}")
        return " | ".join(parts)


class ResumeVectorStore:
    """Vector store for resumes (for matching)."""
    
    def __init__(self):
        self.client = get_chroma_client()
        self.collection = self.client.get_or_create_collection(
            name=RESUMES_COLLECTION,
            metadata={"description": "Resumes for matching"}
        )
    
    def add_resume(self, user_id: int, resume_text: str, skills: List[str]):
        """Add or update a user's resume."""
        # Embed text
        embedding = embed_text(resume_text)
        
        # Add metadata
        metadata = {
            "user_id": int(user_id),
            "skills": ", ".join(skills) if skills else "",
            "text_length": len(resume_text)
        }
        
        # Use user_id as doc id (so we can update later)
        doc_id = f"user_{user_id}"
        
        # Upsert (add or update)
        self.collection.upsert(
            embeddings=[embedding],
            documents=[resume_text],
            metadatas=[metadata],
            ids=[doc_id]
        )
    
    def get_resume(self, user_id: int) -> Optional[Dict]:
        """Get a user's resume from vector store."""
        doc_id = f"user_{user_id}"
        results = self.collection.get(ids=[doc_id])
        
        if results["ids"]:
            return {
                "user_id": user_id,
                "text": results["documents"][0] if results["documents"] else "",
                "metadata": results["metadatas"][0] if results["metadatas"] else {}
            }
        return None
    
    def match_jobs_to_resume(self, user_id: int, n_results: int = 10) -> List[str]:
        """Get job IDs that best match a user's resume."""
        resume = self.get_resume(user_id)
        if not resume:
            return []
        
        # Query jobs collection with resume text
        job_store = JobVectorStore()
        results = job_store.collection.query(
            query_texts=[resume["text"]],
            n_results=n_results
        )
        
        return results["ids"][0] if results["ids"] else []
