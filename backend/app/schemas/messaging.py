from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class InboundMessage(BaseModel):
    sender_phone: str = Field(..., description="E.164 phone number e.g. +919876543210")
    sender_name: Optional[str] = None
    message_text: str
    message_id: Optional[str] = None
    platform: str = "whatsapp" # whatsapp, sms

class OutboundMessageRequest(BaseModel):
    recipient_phone: str
    message_text: str
    is_automated_reply: bool = False
    override_reason: Optional[str] = None

class ContactPolicyCheck(BaseModel):
    phone_number: str
    is_saved_contact: bool
    can_auto_reply: bool
    verdict: str
    reason: str

class MessageResponse(BaseModel):
    status: str
    message_id: Optional[str] = None
    recipient: str
    sent: bool
    reason: Optional[str] = None
    audit_id: Optional[str] = None
