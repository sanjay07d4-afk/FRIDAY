from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
import json
import os

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = Field(default_factory=lambda: int(os.getenv("PORT", 8000)))
    HOST: str = "0.0.0.0"
    TIMEZONE: str = "Asia/Kolkata"

    # Frontend URLs & CORS
    FRONTEND_URL: str = ""
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://*.vercel.app"
    ]

    # Security
    SECRET_KEY: str = "friday-secure-default-change-in-production-random-key"
    API_KEY: str = "friday-dev-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Database (Defaults to local SQLite, adapts to Render Postgres postgresql+asyncpg://)
    DATABASE_URL: str = "sqlite+aiosqlite:///./friday.db"

    # Tasks
    MAX_CONCURRENT_TASKS: int = 5
    DEFAULT_TASK_TIMEOUT_SECONDS: int = 60

    # AI Providers
    AI_PROVIDER: str = "local"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Voice Assistant
    VOICE_STT_PROVIDER: str = "mock"
    VOICE_TTS_PROVIDER: str = "mock"
    SPEAKER_VERIFICATION_THRESHOLD: float = 0.85

    # Messaging
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v20.0"
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    MESSAGING_AUTO_REPLY_ENABLED: bool = False
    MESSAGING_RATE_LIMIT_PER_MINUTE: int = 10

    # Emergency Stop
    EMERGENCY_STOP_ENABLED: bool = False

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        if not v:
            return "sqlite+aiosqlite:///./friday.db"
        # Render PostgreSQL url conversion: postgres:// -> postgresql+asyncpg://
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif v.startswith("sqlite://") and not v.startswith("sqlite+aiosqlite://"):
            return v.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        origins = []
        if isinstance(v, str):
            if v.startswith("["):
                try:
                    origins = json.loads(v)
                except Exception:
                    origins = [v]
            else:
                origins = [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            origins = list(v)

        # Include FRONTEND_URL if provided
        frontend_url = os.getenv("FRONTEND_URL", "").strip()
        if frontend_url and frontend_url not in origins:
            origins.append(frontend_url)

        return origins if origins else ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
