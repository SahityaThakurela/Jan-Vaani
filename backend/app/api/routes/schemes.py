"""
Jan Vaani — Scheme Routes
GET /schemes          → list all schemes
GET /schemes/{id}     → get scheme detail
GET /schemes/search   → Qdrant semantic search
"""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.db_models import Scheme
from app.models.schemas import SchemeOut
from app.services.qdrant_service import qdrant_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=List[SchemeOut])
async def list_schemes(db: AsyncSession = Depends(get_db)):
    """List all seeded schemes."""
    result = await db.execute(select(Scheme))
    return result.scalars().all()


@router.get("/search")
async def search_schemes(
    q: str = Query(..., description="Search query"),
    language: str = Query(default="hi", pattern="^(hi|en)$"),
    limit: int = Query(default=5, ge=1, le=20),
):
    """Semantic search over scheme knowledge using Qdrant."""
    try:
        results = await qdrant_service.search_schemes(q, language, limit)
        return {"query": q, "results": results}
    except Exception as e:
        logger.error(f"Scheme search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/{scheme_id}", response_model=SchemeOut)
async def get_scheme(scheme_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single scheme by ID."""
    result = await db.execute(select(Scheme).where(Scheme.scheme_id == scheme_id))
    scheme = result.scalar_one_or_none()
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{scheme_id}' not found.")
    return scheme
