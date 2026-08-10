"""
Jan Vaani — Qdrant Vector DB Service
Handles:
  - Collection creation (scheme_knowledge + case_memory)
  - Embedding text via Google Gemini text-embedding-004
  - Upserting scheme knowledge chunks
  - Hybrid search (dense + sparse) over scheme_knowledge
"""
import json
import uuid
from typing import Any, Dict, List, Optional
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    SearchRequest, ScoredPoint,
    OptimizersConfigDiff, HnswConfigDiff,
    PayloadSchemaType,
)
import google.generativeai as genai
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QdrantService:
    """Async wrapper around Qdrant for scheme knowledge retrieval."""

    def __init__(self):
        self._client: Optional[AsyncQdrantClient] = None
        self._configured = False

    def _get_client(self) -> AsyncQdrantClient:
        if self._client is None:
            kwargs: Dict[str, Any] = {"url": settings.qdrant_url}
            if settings.qdrant_api_key:
                kwargs["api_key"] = settings.qdrant_api_key
            self._client = AsyncQdrantClient(**kwargs)
        return self._client

    async def _embed(self, text: str) -> List[float]:
        """Get embedding for text using Gemini text-embedding-004."""
        if not settings.gemini_api_key:
            # Return zero vector if no Gemini key (for local dev without key)
            logger.warning("No Gemini API key set — returning zero embedding vector.")
            return [0.0] * settings.embedding_dim

        genai.configure(api_key=settings.gemini_api_key)
        result = genai.embed_content(
            model=settings.gemini_embedding_model,
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]

    async def _embed_query(self, text: str) -> List[float]:
        """Get embedding for a search query."""
        if not settings.gemini_api_key:
            return [0.0] * settings.embedding_dim

        genai.configure(api_key=settings.gemini_api_key)
        result = genai.embed_content(
            model=settings.gemini_embedding_model,
            content=text,
            task_type="retrieval_query",
        )
        return result["embedding"]

    async def ensure_collections(self):
        """Create Qdrant collections if they don't already exist."""
        client = self._get_client()

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
                    indexing_threshold=0,  # index immediately for small collections
                ),
                hnsw_config=HnswConfigDiff(
                    on_disk=False,
                    m=16,
                    ef_construct=100,
                ),
            )
            # Create payload index for fast filtering
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

        # case_memory collection (stretch feature)
        if settings.qdrant_collection_memory not in existing_names:
            await client.create_collection(
                collection_name=settings.qdrant_collection_memory,
                vectors_config=VectorParams(
                    size=settings.embedding_dim,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection: {settings.qdrant_collection_memory}")

    async def upsert_scheme_chunk(
        self,
        scheme_id: str,
        section: str,
        language: str,
        text: str,
        source: str = "seed",
    ) -> str:
        """Embed and upsert a single scheme knowledge chunk."""
        client = self._get_client()
        await self.ensure_collections()

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

    async def search_schemes(
        self,
        query: str,
        language: str = "hi",
        limit: int = 5,
        scheme_id_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid dense search over scheme_knowledge.
        Returns list of {scheme_id, section, text, score} dicts.
        """
        client = self._get_client()
        query_vector = await self._embed_query(query)

        # Build optional filter
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

    async def upsert_case_memory(
        self,
        session_id: str,
        profile: Dict[str, Any],
        scheme_id: str,
        eligible: bool,
        language: str = "hi",
    ) -> str:
        """Store a resolved eligibility case for future similar-case retrieval (stretch)."""
        client = self._get_client()
        await self.ensure_collections()

        # Build a text summary for embedding
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


# Singleton instance
qdrant_service = QdrantService()
