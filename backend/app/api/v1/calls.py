from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.schemas.call import CallInitiateRequest, CallStatusResponse
from app.calls.service import phone_call_service
from app.core.security import verify_auth

router = APIRouter(prefix="/calls", tags=["Phone Call Management"])

@router.post("/initiate", response_model=CallStatusResponse)
async def initiate_call(
    req: CallInitiateRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """Initiates an authorized call workflow with Android companion app contract."""
    res = await phone_call_service.initiate_call_workflow(
        db=db,
        contact_query=req.contact_name_or_number,
        purpose=req.purpose
    )
    if res.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=res["message"])
    elif res.get("status") == "ambiguous":
        raise HTTPException(status_code=400, detail={"message": res["message"], "candidates": res["candidates"]})

    return CallStatusResponse(
        call_id=res.get("call_id", "pending"),
        target=res.get("phone_number", req.contact_name_or_number),
        resolved_contact=res.get("contact_name"),
        status=res.get("status", "initiating"),
        platform="android",
        details=res
    )
