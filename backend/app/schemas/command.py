from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class StepPlan(BaseModel):
    step_id: str
    tool: str
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)

class IntentResult(BaseModel):
    intent: str
    confidence: float
    entities: Dict[str, Any] = Field(default_factory=dict)
    is_ambiguous: bool = False
    clarification_question: Optional[str] = None
    plan: List[StepPlan] = Field(default_factory=list)

class CommandRequest(BaseModel):
    command: str = Field(..., description="Natural language prompt from user")
    session_id: Optional[str] = None
    client_platform: Optional[str] = "web" # web, windows, android

class CommandResponse(BaseModel):
    session_id: str
    command: str
    response_text: str
    intent: IntentResult
    tasks_spawned: List[Dict[str, Any]] = Field(default_factory=list)
    spoken_response: Optional[str] = None
