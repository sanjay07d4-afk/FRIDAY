import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Float, JSON, Text, Enum as SQLEnum
import enum
from app.database.base import Base

class TaskStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_CONFIRMATION = "awaiting_confirmation"

class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(64), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.QUEUED, nullable=False, index=True)
    priority = Column(String(16), default="normal") # low, normal, high, critical
    payload = Column(JSON, default=dict)
    progress = Column(Float, default=0.0) # 0.0 to 1.0
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    timeout_seconds = Column(Float, default=60.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "priority": self.priority,
            "payload": self.payload or {},
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
