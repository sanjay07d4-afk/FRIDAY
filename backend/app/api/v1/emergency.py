from fastapi import APIRouter, Depends
from app.core.emergency import emergency_controller
from app.schemas.call import EmergencyToggleRequest, EmergencyStatusResponse
from app.core.security import verify_auth

router = APIRouter(prefix="/emergency", tags=["Emergency Stop & Safety"])

@router.get("/status", response_model=EmergencyStatusResponse)
async def get_emergency_status(auth: dict = Depends(verify_auth)):
    """Retrieve current emergency stop switch state."""
    return emergency_controller.get_status()

@router.post("/toggle", response_model=EmergencyStatusResponse)
async def toggle_emergency_stop(
    req: EmergencyToggleRequest,
    auth: dict = Depends(verify_auth)
):
    """
    Emergency kill-switch:
    When activated, immediately halts all running tasks, cancels execution tools,
    and blocks all outgoing communications.
    """
    actor = auth.get("sub", "user")
    if req.activate:
        res = await emergency_controller.trigger(triggered_by=actor, reason=req.reason)
    else:
        res = await emergency_controller.reset(reset_by=actor)
    return res
