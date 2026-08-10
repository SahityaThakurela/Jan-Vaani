"""
Jan Vaani — Qdrant Seeder
Run this once after setting up Qdrant to populate scheme_knowledge collection.

Usage:
    cd backend
    python -m app.data.seed_qdrant

Requires:
    - GEMINI_API_KEY set in .env (for embeddings)
    - Qdrant running at QDRANT_URL
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from typing import List

from app.services.qdrant_service import qdrant_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

SEED_FILE = Path(__file__).parent / "schemes_seed.json"

# Sections to chunk from each scheme
CHUNK_CONFIGS = [
    ("description", "description_en", "en"),
    ("description", "description_hi", "hi"),
    ("benefits", "benefits_en", "en"),
    ("benefits", "benefits_hi", "hi"),
]


async def seed():
    logger.info("Starting Qdrant seeding...")

    # Ensure collections exist
    await qdrant_service.ensure_collections()

    with open(SEED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_chunks = 0
    for scheme in data["schemes"]:
        scheme_id = scheme["scheme_id"]
        logger.info(f"Seeding scheme: {scheme_id}")

        for section, field_key, lang in CHUNK_CONFIGS:
            text = scheme.get(field_key, "")
            if not text:
                continue

            # For long texts, chunk by sentence (simple split)
            chunks = _chunk_text(text, max_chars=400)
            for chunk in chunks:
                await qdrant_service.upsert_scheme_chunk(
                    scheme_id=scheme_id,
                    section=section,
                    language=lang,
                    text=chunk,
                    source="seed",
                )
                total_chunks += 1

        # Also index the scheme name + aliases as searchable text
        alias_list = scheme.get("aliases", [])
        alias_text_en = f"{scheme['name_en']}. Also known as: {', '.join(alias_list)}."
        alias_text_hi = f"{scheme['name_hi']}. इसे इन नामों से भी जाना जाता है: {', '.join(alias_list)}."

        await qdrant_service.upsert_scheme_chunk(
            scheme_id=scheme_id, section="name_aliases", language="en",
            text=alias_text_en, source="seed",
        )
        await qdrant_service.upsert_scheme_chunk(
            scheme_id=scheme_id, section="name_aliases", language="hi",
            text=alias_text_hi, source="seed",
        )
        total_chunks += 2

        # Index documents required
        docs = scheme.get("documents_required", [])
        if docs:
            docs_text = f"Documents required for {scheme['name_en']}: {', '.join(docs)}."
            await qdrant_service.upsert_scheme_chunk(
                scheme_id=scheme_id, section="documents", language="en",
                text=docs_text, source="seed",
            )
            docs_text_hi = f"{scheme['name_hi']} के लिए जरूरी दस्तावेज: {', '.join(docs)}."
            await qdrant_service.upsert_scheme_chunk(
                scheme_id=scheme_id, section="documents", language="hi",
                text=docs_text_hi, source="seed",
            )
            total_chunks += 2

    logger.info(f"Qdrant seeding complete. Total chunks upserted: {total_chunks}")


def _chunk_text(text: str, max_chars: int = 400) -> List[str]:
    """Split text into chunks of max_chars characters at sentence boundaries."""
    sentences = text.replace(". ", ".\n").replace("। ", "।\n").split("\n")
    chunks = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) <= max_chars:
            current += (" " if current else "") + sentence.strip()
        else:
            if current:
                chunks.append(current.strip())
            current = sentence.strip()
    if current:
        chunks.append(current.strip())
    return chunks or [text[:max_chars]]


if __name__ == "__main__":
    asyncio.run(seed())
