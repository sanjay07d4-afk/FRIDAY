import asyncio
from datetime import datetime, timezone
import pytz
from typing import Dict, Any, List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.reminder import ReminderModel
from app.database.session import AsyncSessionLocal
from app.tasks.engine import task_engine

class PersistentSchedulerService:
    """
    Timezone-aware, database-persisted scheduler for FRIDAY reminders and automation.
    Survives application restarts and handles missed executions cleanly.
    """
    def __init__(self, default_timezone: str = "Asia/Kolkata"):
        self.tz = pytz.timezone(default_timezone)
        self.scheduler = AsyncIOScheduler(timezone=self.tz)
        self._is_running = False

    def start(self):
        if not self._is_running:
            self.scheduler.start()
            self._is_running = True

    def shutdown(self):
        if self._is_running:
            self.scheduler.shutdown(wait=False)
            self._is_running = False

    async def reload_pending_reminders(self, session_factory=None):
        """Load pending scheduled reminders from database on startup"""
        session_maker = session_factory or AsyncSessionLocal
        async with session_maker() as session:
            stmt = select(ReminderModel).where(ReminderModel.status == "scheduled")
            result = await session.execute(stmt)
            reminders = result.scalars().all()
            for r in reminders:
                self._schedule_job_in_apscheduler(r)

    def _schedule_job_in_apscheduler(self, reminder: ReminderModel):
        job_id = f"reminder_{reminder.id}"
        # Remove existing if already present
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        target_tz = pytz.timezone(reminder.timezone or settings.TIMEZONE)

        if reminder.cron_expression:
            # Recurring cron
            parts = reminder.cron_expression.split()
            if len(parts) == 5:
                minute, hour, dom, month, dow = parts
                trigger = CronTrigger(
                    minute=minute, hour=hour, day=dom, month=month, day_of_week=dow, timezone=target_tz
                )
                self.scheduler.add_job(
                    self._execute_reminder_job,
                    trigger=trigger,
                    id=job_id,
                    args=[reminder.id],
                    replace_existing=True
                )
        elif reminder.due_at:
            # One-time date trigger
            run_time = reminder.due_at
            if run_time.tzinfo is None:
                # SQLite stores naive UTC datetime
                run_time = pytz.UTC.localize(run_time)
            else:
                run_time = run_time.astimezone(pytz.UTC)

            now = datetime.now(timezone.utc)
            if run_time > now:
                self.scheduler.add_job(
                    self._execute_reminder_job,
                    trigger=DateTrigger(run_date=run_time.astimezone(target_tz), timezone=target_tz),
                    id=job_id,
                    args=[reminder.id],
                    replace_existing=True
                )

    async def _execute_reminder_job(self, reminder_id: str):
        async with AsyncSessionLocal() as session:
            stmt = select(ReminderModel).where(ReminderModel.id == reminder_id)
            result = await session.execute(stmt)
            reminder = result.scalar_one_or_none()
            if not reminder or reminder.status != "scheduled":
                return

            # Spawn reminder alert task into task engine
            await task_engine.create_and_enqueue_task(
                task_type="timer",
                title=f"Reminder Alert: {reminder.title}",
                payload={"reminder_id": reminder.id, "due_at": reminder.due_at.isoformat() if reminder.due_at else None}
            )

            if not reminder.is_recurring:
                reminder.status = "completed"
                reminder.updated_at = datetime.now(timezone.utc)
                await session.commit()

    async def create_reminder(
        self,
        db: AsyncSession,
        title: str,
        due_at: Optional[datetime] = None,
        cron_expression: Optional[str] = None,
        description: Optional[str] = None,
        timezone_str: str = "Asia/Kolkata",
        is_recurring: bool = False,
        payload: Dict[str, Any] = None
    ) -> ReminderModel:
        if not due_at and not cron_expression:
            raise ValueError("Ambiguous reminder: Must provide either a due_at timestamp or a cron_expression.")

        reminder = ReminderModel(
            title=title,
            description=description,
            due_at=due_at,
            cron_expression=cron_expression,
            timezone=timezone_str,
            is_recurring=is_recurring,
            status="scheduled",
            payload=payload or {}
        )
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)

        self._schedule_job_in_apscheduler(reminder)
        return reminder

    async def cancel_reminder(self, db: AsyncSession, reminder_id: str) -> Optional[ReminderModel]:
        stmt = select(ReminderModel).where(ReminderModel.id == reminder_id)
        result = await db.execute(stmt)
        reminder = result.scalar_one_or_none()
        if not reminder:
            return None

        reminder.status = "cancelled"
        reminder.updated_at = datetime.now(timezone.utc)
        await db.commit()

        job_id = f"reminder_{reminder_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        return reminder

    async def list_reminders(self, db: AsyncSession, status: Optional[str] = None) -> List[ReminderModel]:
        stmt = select(ReminderModel)
        if status:
            stmt = stmt.where(ReminderModel.status == status)
        stmt = stmt.order_by(ReminderModel.due_at.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

scheduler_service = PersistentSchedulerService(default_timezone=settings.TIMEZONE)
