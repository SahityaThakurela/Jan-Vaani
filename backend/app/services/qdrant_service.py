"""
Jan Vaani — Qdrant Vector DB Service
Handles:
  - Collection creation (scheme_knowledge + case_memory)
  - Embedding text via Google Gemini text-embedding-004
  - Upserting scheme knowledge chunks
  - Hybrid search (dense + sparse) over scheme_knowledge

NOTE: All methods fail gracefully if Qdrant is not running locally.
      The voice pipeline continues to work without vector search in that case.
"""
import json
import uuid
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Lazily import qdrant_client so a missing install doesn't crash startup
try:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct,
        Filter, FieldCondition, MatchValue,
        ScoredPoint,
        OptimizersConfigDiff, HnswConfigDiff,
        PayloadSchemaType,
    )
    _QDRANT_AVAILABLE = True
except ImportError:
    _QDRANT_AVAILABLE = False
    logger.warning("qdrant-client not installed — vector search disabled.")


class QdrantService:
    """Async wrapper around Qdrant for scheme knowledge retrieval."""

    def __init__(self):
        self._client = None
        self._available = _QDRANT_AVAILABLE
        self._checked = False  # have we tried connecting yet?
        self._gemini_client = None

    def _get_client(self):
        if not self._available:
            return None
        if self._client is None:
            kwargs: Dict[str, Any] = {"url": settings.qdrant_url}
            if settings.qdrant_api_key:
                kwargs["api_key"] = settings.qdrant_api_key
            self._client = AsyncQdrantClient(**kwargs)
        return self._client
        
    def _get_gemini_client(self) -> Optional[genai.Client]:
        if not settings.gemini_api_key:
            return None
        if self._gemini_client is None:
            self._gemini_client = genai.Client(api_key=settings.gemini_api_key)
        return self._gemini_client

    async def _embed(self, text: str) -> List[float]:
        """Get embedding for text using Gemini text-embedding-004."""
        gemini_client = self._get_gemini_client()
        if not gemini_client:
            logger.warning("No Gemini API key set — returning zero embedding vector.")
            return [0.0] * settings.embedding_dim

        result = await gemini_client.aio.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        return result.embeddings[0].values

    async def _embed_query(self, text: str) -> List[float]:
        """Get embedding for a search query."""
        gemini_client = self._get_gemini_client()
        if not gemini_client:
            return [0.0] * settings.embedding_dim

        result = await gemini_client.aio.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return result.embeddings[0].values

    async def ensure_collections(self) -> bool:
        """Create Qdrant collections if they don't already exist. Returns True on success."""
        client = self._get_client()
        if client is None:
            return False
        try:
            existing = await client.get_collections()
            existing_names = {c.name for c in existing.collections}

            # scheme_knowledge collection
            if settings.qdrant_collection_scheme not in existing_names:
                await client.create_collection(
                    collection_name=settings.qdrant_collection_scheme,
                    vectors_config=VectorParams(
                        size=settings.embedding_dim,
                        distance=Distance.COSINE,
                    ),
                    optimizers_config=OptimizersConfigDiff(
                        indexing_threshold=0,
                    ),
                    hnsw_config=HnswConfigDiff(
                        on_disk=False,
                        m=16,
                        ef_construct=100,
                    ),
                )
                await client.create_payload_index(
                    collection_name=settings.qdrant_collection_scheme,
                    field_name="scheme_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                await client.create_payload_index(
                    collection_name=settings.qdrant_collection_scheme,
                    field_name="language",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                logger.info(f"Created collection: {settings.qdrant_collection_scheme}")

            # case_memory collection
            if settings.qdrant_collection_memory not in existing_names:
                await client.create_collection(
                    collection_name=settings.qdrant_collection_memory,
                    vectors_config=VectorParams(
                        size=settings.embedding_dim,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Created collection: {settings.qdrant_collection_memory}")
            return True
        except Exception as e:
            logger.warning(f"Qdrant not reachable (collections check failed): {e} — vector search disabled.")
            self._available = False
            return False

    async def upsert_scheme_chunk(
        self,
        scheme_id: str,
        section: str,
        language: str,
        text: str,
        source: str = "seed",
    ) -> Optional[str]:
        """Embed and upsert a single scheme knowledge chunk."""
        client = self._get_client()
        if client is None:
            return None
        try:
            ok = await self.ensure_collections()
            if not ok:
                return None
            vector = await self._embed(text)
            point_id = str(uuid.uuid4())
            await client.upsert(
                collection_name=settings.qdrant_collection_scheme,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "scheme_id": scheme_id,
                            "language": language,
                            "section": section,
                            "source": source,
                            "text": text,
                        },
                    )
                ],
            )
            logger.debug(f"Upserted chunk [{scheme_id}/{section}/{language}]")
            return point_id
        except Exception as e:
            logger.warning(f"Qdrant upsert failed (non-critical): {e}")
            return None

    async def search_schemes(
        self,
        query: str,
        language: str = "hi",
        limit: int = 5,
        scheme_id_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Dense vector search over scheme_knowledge.
        Returns [] gracefully if Qdrant is unavailable.
        """
        client = self._get_client()
        if client is None:
            return []
        try:
            query_vector = await self._embed_query(query)

            filters = [FieldCondition(key="language", match=MatchValue(value=language))]
            if scheme_id_filter:
                filters.append(FieldCondition(key="scheme_id", match=MatchValue(value=scheme_id_filter)))
            qdrant_filter = Filter(must=filters) if filters else None

            results: List[ScoredPoint] = await client.search(
                collection_name=settings.qdrant_collection_scheme,
                query_vector=query_vector,
                query_filter=qdrant_filter,
                limit=limit,
                with_payload=True,
                score_threshold=0.2,
            )
            return [
                {
                    "scheme_id": r.payload.get("scheme_id"),
                    "section": r.payload.get("section"),
                    "text": r.payload.get("text"),
                    "score": r.score,
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Qdrant search failed (non-critical): {e}")
            return []

    async def upsert_case_memory(
        self,
        session_id: str,
        profile: Dict[str, Any],
        scheme_id: str,
        eligible: bool,
        language: str = "hi",
    ) -> Optional[str]:
        """Store a resolved eligibility case for future similar-case retrieval."""
        client = self._get_client()
        if client is None:
            return None
        try:
            ok = await self.ensure_collections()
            if not ok:
                return None
            profile_text = " | ".join(f"{k}: {v}" for k, v in profile.items())
            summary = f"Scheme: {scheme_id}. Eligible: {eligible}. Profile: {profile_text}"
            vector = await self._embed(summary)
            point_id = str(uuid.uuid4())
            await client.upsert(
                collection_name=settings.qdrant_collection_memory,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "session_id": session_id,
                            "scheme_id": scheme_id,
                            "eligible": eligible,
                            "profile": profile,
                            "language": language,
                            "summary": summary,
                        },
                    )
                ],
            )
            return point_id
        except Exception as e:
            logger.warning(f"Case memory upsert failed (non-critical): {e}")
            return None


# Singleton instance
qdrant_service = QdrantService()