from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class ReminderCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_at: Optional[str] = Field(None, description="ISO-8601 string for one-time reminder")
    cron_expression: Optional[str] = Field(None, description="Standard cron string for recurring task")
    timezone: str = "Asia/Kolkata"
    is_recurring: bool = False
    payload: Dict[str, Any] = Field(default_factory=dict)

class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_at: Optional[str] = None
    cron_expression: Optional[str] = None
    status: Optional[str] = None

class ReminderResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    due_at: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: str
    is_recurring: bool
    status: str
    payload: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
