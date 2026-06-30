
"""Semantic search API routes."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from agent.semantic_search import SemanticJobSearch


router = APIRouter(prefix="/api/semantic", tags=["semantic-search"])


class IndexJobsRequest(BaseModel):
    """Request to index jobs into vector store."""
    jobs: List[dict]


@router.post("/index")
async def index_jobs(req: IndexJobsRequest):
    """Add jobs to semantic search index."""
    try:
        search = SemanticJobSearch()
        count = search.add_jobs_to_index(req.jobs)
        stats = search.get_index_stats()
        
        return {
            "indexed": count,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def semantic_search(
    query: str = Query(..., description="Search query"),
    user_id: Optional[int] = None,
    use_resume: Optional[bool] = False,
    n_results: int = Query(10, ge=1, le=50),
    filter_remote: Optional[bool] = None
):
    """
    Semantic search for jobs matching query.
    Optionally use user's stored resume instead of explicit query.
    """
    try:
        search = SemanticJobSearch()
        results = search.search(
            query=query,
            user_id=user_id,
            n_results=n_results,
            use_resume=use_resume,
            filter_remote=filter_remote
        )
        
        return {
            "query": query,
            "used_resume": use_resume and user_id is not None,
            "total_results": len(results),
            "jobs": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """Get vector store statistics."""
    try:
        search = SemanticJobSearch()
        return search.get_index_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
