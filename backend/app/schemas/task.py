from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

class TaskCreate(BaseModel):
    type: str = Field(..., description="Task type identifier e.g. weather, timer, summarize, open_app")
    title: str = Field(..., description="Human readable task title")
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: str = Field(default="normal", description="low, normal, high, critical")
    timeout_seconds: float = Field(default=60.0)

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class TaskResponse(BaseModel):
    id: str
    type: str
    title: str
    status: str
    priority: str
    payload: Dict[str, Any]
    progress: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timeout_seconds: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class TaskBatchRequest(BaseModel):
    tasks: List[TaskCreate]
