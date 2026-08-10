"""
Jan Vaani — DB Initialization + Seeding
Creates all tables and seeds scheme data from schemes_seed.json
"""
import json
import os
from pathlib import Path
from sqlalchemy import select, text
from app.db.database import engine, Base
from app.models.db_models import Scheme, SchemeEligibilityRule, SchemeRequiredSlot
from app.utils.logger import get_logger

logger = get_logger(__name__)

SEED_FILE = Path(__file__).parent.parent / "data" / "schemes_seed.json"


async def initialize_database():
    """Create tables and seed data on startup."""
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All tables created (or already exist).")
    await seed_schemes()


async def seed_schemes():
    """Seed scheme data if not already present."""
    if not SEED_FILE.exists():
        logger.warning(f"Seed file not found: {SEED_FILE}")
        return

    with open(SEED_FILE, "r", encoding="utf-8") as f:
        seed_data = json.load(f)

    from app.db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        for scheme_data in seed_data.get("schemes", []):
            # Check if scheme already exists
            result = await session.execute(
                select(Scheme).where(Scheme.scheme_id == scheme_data["scheme_id"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.debug(f"Scheme {scheme_data['scheme_id']} already seeded, skipping.")
                continue

            # Insert scheme
            scheme = Scheme(
                scheme_id=scheme_data["scheme_id"],
                name_en=scheme_data["name_en"],
                name_hi=scheme_data["name_hi"],
                aliases=json.dumps(scheme_data.get("aliases", [])),
                category=scheme_data["category"],
                description_en=scheme_data.get("description_en"),
                description_hi=scheme_data.get("description_hi"),
                benefits_en=scheme_data.get("benefits_en"),
                benefits_hi=scheme_data.get("benefits_hi"),
                documents_required=json.dumps(scheme_data.get("documents_required", [])),
                official_url=scheme_data.get("official_url"),
            )
            session.add(scheme)

            # Insert eligibility rules
            for rule in scheme_data.get("eligibility_rules", []):
                session.add(SchemeEligibilityRule(
                    scheme_id=scheme_data["scheme_id"],
                    field_name=rule["field_name"],
                    operator=rule["operator"],
                    value=str(rule["value"]),
                    value_type=rule["value_type"],
                    description=rule.get("description"),
                ))

            # Insert required slots
            for slot in scheme_data.get("required_slots", []):
                session.add(SchemeRequiredSlot(
                    scheme_id=scheme_data["scheme_id"],
                    slot_name=slot["slot_name"],
                    slot_type=slot["slot_type"],
                    question_text_en=slot["question_text_en"],
                    question_text_hi=slot["question_text_hi"],
                    priority=slot.get("priority", 100),
                ))

            await session.commit()
            logger.info(f"Seeded scheme: {scheme_data['name_en']}")

    logger.info("Scheme seeding complete.")
