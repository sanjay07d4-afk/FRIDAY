import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Text
from app.database.base import Base

class ContactModel(Base):
    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False)
    phone_number = Column(String(32), unique=True, index=True, nullable=False)
    is_saved = Column(Boolean, default=True, index=True) # SAVED vs UNSAVED
    auto_reply_permitted = Column(Boolean, default=False) # STRICT POLICY
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone_number": self.phone_number,
            "is_saved": self.is_saved,
            "auto_reply_permitted": self.auto_reply_permitted,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
