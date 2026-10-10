import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean
from app.database.base import Base

class ReminderModel(Base):
    __tablename__ = "reminders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    due_at = Column(DateTime, nullable=True, index=True)
    cron_expression = Column(String(64), nullable=True)
    timezone = Column(String(64), default="Asia/Kolkata")
    is_recurring = Column(Boolean, default=False)
    status = Column(String(32), default="scheduled", index=True) # scheduled, completed, cancelled, missed
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "cron_expression": self.cron_expression,
            "timezone": self.timezone,
            "is_recurring": self.is_recurring,
            "status": self.status,
            "payload": self.payload or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
