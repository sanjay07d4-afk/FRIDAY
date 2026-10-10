from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db
from app.schemas.call import DeviceRegisterRequest, DeviceResponse
from app.models.device import DeviceModel
from app.core.security import verify_auth, get_password_hash
import uuid

router = APIRouter(prefix="/devices", tags=["Device Registration & Agents"])

@router.post("/register", response_model=DeviceResponse)
async def register_device(
    req: DeviceRegisterRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """Register a Windows desktop agent or Android companion client."""
    device_id = str(uuid.uuid4())
    raw_api_key = f"devkey_{uuid.uuid4().hex}"
    key_hash = get_password_hash(raw_api_key)

    device = DeviceModel(
        id=device_id,
        device_name=req.device_name,
        platform=req.platform,
        api_key_hash=key_hash,
        capabilities=req.capabilities,
        is_active=True
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)

    resp = device.to_dict()
    resp["api_key"] = raw_api_key # Return key once on registration
    return resp

@router.get("", response_model=List[DeviceResponse])
async def list_devices(
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """List registered client agents and devices."""
    stmt = select(DeviceModel).where(DeviceModel.is_active == True)
    res = await db.execute(stmt)
    return [d.to_dict() for d in res.scalars().all()]
