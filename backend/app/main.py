"""
Jan Vaani — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.utils.logger import get_logger
from app.db.init_db import initialize_database
from app.api.routes import session, voice, schemes, eligibility, handoff, auth, chat

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version} [{settings.environment}]")
    # Initialize SQLite DB + seed schemes on startup
    await initialize_database()
    logger.info("Database initialized and seeded.")
    yield
    logger.info(f"{settings.app_name} shutting down.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Jan Vaani — A voice-first AI platform for rural Indian users to access "
        "government welfare schemes in their own language, hands-free."
    ),
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(session.router, prefix="/sessions", tags=["Sessions"])
app.include_router(voice.router, prefix="/voice", tags=["Voice Pipeline"])
app.include_router(schemes.router, prefix="/schemes", tags=["Schemes"])
app.include_router(eligibility.router, prefix="/eligibility", tags=["Eligibility"])
app.include_router(handoff.router, prefix="/handoff", tags=["Handoff"])
app.include_router(chat.router, prefix="/chat", tags=["Text Chat"])



@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "environment": settings.environment}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."},
    )
