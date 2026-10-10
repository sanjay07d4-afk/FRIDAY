from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.schemas.reminder import ReminderCreate, ReminderResponse
from app.scheduler.service import scheduler_service
from app.core.security import verify_auth

router = APIRouter(prefix="/reminders", tags=["Scheduler & Reminders"])

@router.post("", response_model=ReminderResponse)
async def create_reminder(
    reminder_in: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """Schedule a one-time or recurring reminder with timezone awareness."""
    due_dt = None
    if reminder_in.due_at:
        try:
            due_dt = datetime.fromisoformat(reminder_in.due_at.replace("Z", "+00:00"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ISO-8601 format for due_at timestamp.")

    try:
        reminder = await scheduler_service.create_reminder(
            db=db,
            title=reminder_in.title,
            due_at=due_dt,
            cron_expression=reminder_in.cron_expression,
            description=reminder_in.description,
            timezone_str=reminder_in.timezone,
            is_recurring=reminder_in.is_recurring,
            payload=reminder_in.payload
        )
        return reminder.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[ReminderResponse])
async def list_reminders(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """List scheduled reminders and jobs."""
    reminders = await scheduler_service.list_reminders(db=db, status=status)
    return [r.to_dict() for r in reminders]

@router.delete("/{reminder_id}", response_model=ReminderResponse)
async def cancel_reminder(
    reminder_id: str,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """Cancel a scheduled reminder."""
    reminder = await scheduler_service.cancel_reminder(db=db, reminder_id=reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder.to_dict()
