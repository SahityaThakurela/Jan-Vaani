"""SQLAlchemy database engine and session factory."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# SQLite async URL
DATABASE_URL = f"sqlite+aiosqlite:///{settings.sqlite_db_path}"

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.is_development,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
