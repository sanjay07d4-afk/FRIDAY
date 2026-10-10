import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, JSON
from app.database.base import Base

class DeviceModel(Base):
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_name = Column(String(128), nullable=False)
    platform = Column(String(32), nullable=False) # windows, android, web
    api_key_hash = Column(String(128), nullable=False)
    capabilities = Column(JSON, default=list) # e.g. ["open_app", "media_control", "contacts"]
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "device_name": self.device_name,
            "platform": self.platform,
            "capabilities": self.capabilities or [],
            "is_active": self.is_active,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
