from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone
from app.database.session import get_db
from app.core.emergency import emergency_controller
from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])

@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Comprehensive health check endpoint providing service readiness and database connectivity."""
    db_healthy = False
    try:
        await db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception:
        db_healthy = False

    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "FRIDAY AI Core Backend",
        "version": "1.0.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "database_connected": db_healthy,
        "emergency_stop_active": emergency_controller.is_active,
        "environment": settings.ENVIRONMENT,
        "timezone": settings.TIMEZONE
    }
