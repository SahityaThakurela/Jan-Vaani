"""
Jan Vaani — Central Configuration
All settings are loaded from the .env file via pydantic-settings.
Never hardcode secrets here.
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────
    app_name: str = "Jan Vaani"
    app_version: str = "1.0.0"
    environment: str = "development"
    app_secret_key: str = "changeme"

    # ── JWT Auth ─────────────────────────────────────────────
    jwt_secret_key: str = "your-jwt-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7   # 7 days for hackathon convenience

    # ── Database ─────────────────────────────────────────────
    sqlite_db_path: str = "./janvaani.db"

    # ── Rime TTS (Coda model) ─────────────────────────────────
    rime_api_key: str = Field(..., description="Rime API Key")
    rime_api_url: str = "https://users.rime.ai/v1/rime-tts"
    rime_model: str = "mist"          # "mist" = Coda model per Rime docs
    rime_speaker: str = "maya"        # Indian English voice
    rime_audio_format: str = "mp3"
    rime_sampling_rate: int = 22050

    # ── Google Gemini ─────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"          # stable model name
    gemini_embedding_model: str = "models/text-embedding-004"

    # ── Deepgram STT ──────────────────────────────────────────
    deepgram_api_key: str = ""
    deepgram_model: str = "nova-2"
    deepgram_language: str = "hi-IN"

    # ── Qdrant ────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection_scheme: str = "scheme_knowledge"
    qdrant_collection_memory: str = "case_memory"
    embedding_dim: int = 768

    # ── CORS ──────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
