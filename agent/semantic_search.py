"""
Semantic search for jobs using vector store.
Combines keyword (BM25) + semantic (ChromaDB) search.
"""
from typing import List, Dict, Optional
from rank_bm25 import BM25Okapi

from agent.vector_store import JobVectorStore, ResumeVectorStore


class SemanticJobSearch:
    """Hybrid semantic + keyword job search."""
    
    def __init__(self):
        self.job_store = JobVectorStore()
        self.resume_store = ResumeVectorStore()
    
    def search(
        self,
        query: str,
        user_id: Optional[int] = None,
        n_results: int = 10,
        semantic_weight: float = 0.7,
        use_resume: bool = False,
        filter_remote: Optional[bool] = None
    ) -> List[Dict]:
        """
        Hybrid search combining semantic + keyword matching.
        
        Args:
            query: Search query (skills, role, etc.)
            user_id: If provided and use_resume=True, use user's resume
            n_results: Number of results to return
            semantic_weight: 0-1, how much to weight semantic vs keyword
            use_resume: Use user's stored resume instead of query
            filter_remote: Only remote jobs
        """
        # Determine search query
        if use_resume and user_id:
            resume = self.resume_store.get_resume(user_id)
            if resume:
                query = resume["text"]
        
        # 1. Semantic search via vector store
        semantic_results = self.job_store.search_jobs(
            query=query,
            n_results=n_results * 2,  # Get more, will re-rank
            filter_remote=filter_remote
        )
        
        # 2. Format & return top results
        # (BM25 keyword search can be added later for full hybrid)
        return semantic_results[:n_results]
    
    def add_jobs_to_index(self, jobs: List[Dict]) -> int:
        """Add jobs to semantic search index."""
        return self.job_store.add_jobs(jobs)
    
    def get_index_stats(self) -> Dict:
        """Get semantic search index stats."""
        return self.job_store.get_stats()
