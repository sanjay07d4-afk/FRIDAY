from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db
from app.schemas.messaging import InboundMessage, OutboundMessageRequest, MessageResponse, ContactPolicyCheck
from app.messaging.service import messaging_service
from app.models.contact import ContactModel
from app.core.security import verify_auth

router = APIRouter(prefix="/messaging", tags=["WhatsApp & Messaging Automation"])

@router.post("/send", response_model=MessageResponse)
async def send_message(
    req: OutboundMessageRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """Send an outbound message via verified provider."""
    result = await messaging_service.send_message(
        db=db,
        recipient_phone=req.recipient_phone,
        message_text=req.message_text,
        is_automated=req.is_automated_reply
    )
    return {
        "status": "sent" if result["sent"] else "failed",
        "recipient": req.recipient_phone,
        "sent": result["sent"],
        "reason": result.get("reason"),
        "audit_id": result.get("audit_id")
    }

@router.post("/inbound")
async def handle_inbound_message(
    inbound: InboundMessage,
    db: AsyncSession = Depends(get_db)
):
    """
    Inbound message webhook endpoint.
    Applies strict contact policy: NEVER automatically reply to saved contacts.
    """
    result = await messaging_service.process_inbound_message(
        db=db,
        sender_phone=inbound.sender_phone,
        message_text=inbound.message_text,
        sender_name=inbound.sender_name,
        platform=inbound.platform
    )
    return result

@router.get("/policy-check", response_model=ContactPolicyCheck)
async def check_contact_policy(
    phone_number: str = Query(..., description="Phone number to check"),
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """Inspects policy compliance for a specific contact phone number."""
    policy = await messaging_service.verify_contact_policy(db, phone_number)
    return ContactPolicyCheck(
        phone_number=policy["phone_number"],
        is_saved_contact=policy["is_saved_contact"],
        can_auto_reply=policy["can_auto_reply"],
        verdict=policy["verdict"],
        reason=policy["reason"]
    )

@router.post("/contacts")
async def register_contact(
    name: str,
    phone_number: str,
    is_saved: bool = True,
    auto_reply_permitted: bool = False,
    notes: str = None,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """Explicitly register a contact into the address book with saved/unsaved status."""
    clean_phone = phone_number.strip().replace(" ", "").replace("-", "")
    stmt = select(ContactModel).where(ContactModel.phone_number == clean_phone)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        existing.name = name
        existing.is_saved = is_saved
        existing.auto_reply_permitted = auto_reply_permitted
        existing.notes = notes
        await db.commit()
        await db.refresh(existing)
        return existing.to_dict()

    contact = ContactModel(
        name=name,
        phone_number=clean_phone,
        is_saved=is_saved,
        auto_reply_permitted=auto_reply_permitted,
        notes=notes
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact.to_dict()
