from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class MemoryCreate(BaseModel):
    category: str = Field(default="fact", description="fact, preference, instruction, summary")
    content: str = Field(..., description="Fact or instruction to remember")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MemoryUpdate(BaseModel):
    category: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class MemoryResponse(BaseModel):
    id: str
    user_id: str
    category: str
    content: str
    metadata: Dict[str, Any]
    is_deleted: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class MemorySearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    limit: int = 10
