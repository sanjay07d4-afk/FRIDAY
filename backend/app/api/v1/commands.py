from fastapi import APIRouter, Depends
from app.schemas.command import CommandRequest, CommandResponse
from app.ai.orchestrator import ai_orchestrator
from app.core.security import verify_auth

router = APIRouter(prefix="/commands", tags=["Core AI Commands"])

@router.post("", response_model=CommandResponse)
async def submit_command(req: CommandRequest, auth: dict = Depends(verify_auth)):
    """
    Submits a natural-language command to FRIDAY AI.
    Decomposes intent, plans execution, spawns tasks, and returns conversational response.
    """
    session_id = req.session_id or auth.get("sub", "default_session")
    response = await ai_orchestrator.process_command(
        text=req.command,
        session_id=session_id,
        platform=req.client_platform or "web"
    )
    return response
