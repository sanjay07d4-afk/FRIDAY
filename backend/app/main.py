from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.session import init_db
from app.scheduler.service import scheduler_service
from app.api.v1 import (
    health,
    tasks,
    commands,
    memory,
    reminders,
    messaging,
    calls,
    voice,
    emergency,
    devices,
    ws
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database tables and persistent scheduler
    print("[FRIDAY Core] Initializing database persistence layer...")
    await init_db()
    print("[FRIDAY Core] Starting persistent scheduler...")
    scheduler_service.start()
    await scheduler_service.reload_pending_reminders()
    print(f"[FRIDAY Core] Online. Timezone: {settings.TIMEZONE} | Environment: {settings.ENVIRONMENT}")
    yield
    # Shutdown: Graceful cleanup
    print("[FRIDAY Core] Shutting down scheduler and active connections...")
    scheduler_service.shutdown()

app = FastAPI(
    title="FRIDAY AI — Backend Service",
    description="Production-grade AI Assistant Backend Orchestration Layer for FRIDAY",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Routers
api_v1_prefix = "/api/v1"
app.include_router(health.router, prefix=api_v1_prefix)
app.include_router(tasks.router, prefix=api_v1_prefix)
app.include_router(commands.router, prefix=api_v1_prefix)
app.include_router(memory.router, prefix=api_v1_prefix)
app.include_router(reminders.router, prefix=api_v1_prefix)
app.include_router(messaging.router, prefix=api_v1_prefix)
app.include_router(calls.router, prefix=api_v1_prefix)
app.include_router(voice.router, prefix=api_v1_prefix)
app.include_router(emergency.router, prefix=api_v1_prefix)
app.include_router(devices.router, prefix=api_v1_prefix)

# Include WebSockets
app.include_router(ws.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
