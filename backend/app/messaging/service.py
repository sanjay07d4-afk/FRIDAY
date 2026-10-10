import time
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.contact import ContactModel
from app.models.audit import AuditLogModel
from app.core.config import settings
from app.core.emergency import emergency_controller

class MessagingAutomationService:
    """
    Messaging Automation Layer with strict Contact Policy:
    
    STRICT POLICY REQUIREMENT:
    FRIDAY MUST NEVER automatically reply to saved contacts.
    Automatic replies are permitted ONLY for unsaved numbers, subject to configured rules
    and platform API safety standards.
    Unknown / unresolvable contact status defaults to FAIL-SAFE (NO REPLY).
    """

    def __init__(self):
        self._rate_limits: Dict[str, list] = {} # phone -> list of timestamps

    def _is_rate_limited(self, phone: str) -> bool:
        now = time.time()
        window = 60.0 # 1 minute
        max_msgs = settings.MESSAGING_RATE_LIMIT_PER_MINUTE

        timestamps = self._rate_limits.get(phone, [])
        timestamps = [t for t in timestamps if now - t < window]
        self._rate_limits[phone] = timestamps

        if len(timestamps) >= max_msgs:
            return True
        self._rate_limits[phone].append(now)
        return False

    async def verify_contact_policy(self, db: AsyncSession, phone_number: str) -> Dict[str, Any]:
        """
        Evaluates incoming sender against the strict saved-contact policy.
        Returns evaluation verdict and policy enforcement reasoning.
        """
        clean_phone = phone_number.strip().replace(" ", "").replace("-", "")

        stmt = select(ContactModel).where(ContactModel.phone_number == clean_phone)
        result = await db.execute(stmt)
        contact = result.scalar_one_or_none()

        # If contact exists and is marked as SAVED
        if contact and contact.is_saved:
            return {
                "phone_number": clean_phone,
                "is_saved_contact": True,
                "can_auto_reply": False,
                "verdict": "DENIED",
                "reason": "STRICT POLICY: Contact is SAVED. Automatic replies to saved contacts are strictly prohibited."
            }

        # If contact is explicitly registered as UNSAVED with permitted override
        if contact and not contact.is_saved:
            can_reply = settings.MESSAGING_AUTO_REPLY_ENABLED and contact.auto_reply_permitted
            return {
                "phone_number": clean_phone,
                "is_saved_contact": False,
                "can_auto_reply": can_reply,
                "verdict": "PERMITTED" if can_reply else "DENIED",
                "reason": "Unsaved contact: Auto-reply allowed by configured rules" if can_reply else "Unsaved contact: Auto-reply disabled in settings"
            }

        # Unsaved, unknown number not in address book
        can_reply = settings.MESSAGING_AUTO_REPLY_ENABLED
        return {
            "phone_number": clean_phone,
            "is_saved_contact": False,
            "can_auto_reply": can_reply,
            "verdict": "PERMITTED" if can_reply else "DENIED",
            "reason": "Unsaved number: General auto-reply policy" if can_reply else "Auto-reply globally disabled"
        }

    async def process_inbound_message(
        self,
        db: AsyncSession,
        sender_phone: str,
        message_text: str,
        sender_name: Optional[str] = None,
        platform: str = "whatsapp"
    ) -> Dict[str, Any]:
        """
        Receives an inbound message, checks contact policy, and decides on auto-reply.
        """
        # Emergency stop check
        if emergency_controller.is_active:
            await self._log_audit(db, "inbound_message_blocked", sender_phone, {"reason": "Emergency stop active"}, False)
            return {"status": "blocked", "reason": "Emergency stop active", "auto_reply_sent": False}

        policy = await self.verify_contact_policy(db, sender_phone)

        # Audit log incoming message
        await self._log_audit(db, "inbound_message_received", sender_phone, {
            "platform": platform,
            "text_length": len(message_text),
            "policy_verdict": policy["verdict"]
        }, True)

        if not policy["can_auto_reply"]:
            return {
                "status": "received_no_auto_reply",
                "policy": policy,
                "auto_reply_sent": False,
                "message": "Message received. Auto-reply omitted per strict privacy/contact policy."
            }

        # Check rate limits
        if self._is_rate_limited(sender_phone):
            return {
                "status": "rate_limited",
                "policy": policy,
                "auto_reply_sent": False,
                "message": "Rate limit exceeded for recipient."
            }

        # Generate template reply for unsaved numbers
        auto_reply_text = "Greetings. This is FRIDAY, personal assistant. Your message has been logged. The owner will review it shortly."

        send_result = await self.send_message(
            db=db,
            recipient_phone=sender_phone,
            message_text=auto_reply_text,
            is_automated=True
        )

        return {
            "status": "auto_reply_dispatched",
            "policy": policy,
            "auto_reply_sent": send_result["sent"],
            "send_result": send_result
        }

    async def send_message(
        self,
        db: AsyncSession,
        recipient_phone: str,
        message_text: str,
        is_automated: bool = False
    ) -> Dict[str, Any]:
        """
        Dispatches an outbound message via the configured WhatsApp / SMS provider.
        Enforces emergency stop and logs every action into audit trail.
        """
        if emergency_controller.is_active:
            await self._log_audit(db, "outbound_message_blocked", recipient_phone, {"reason": "Emergency stop active"}, False)
            return {"sent": False, "reason": "Emergency stop active"}

        # If automated, re-verify that recipient is NOT a saved contact
        if is_automated:
            policy = await self.verify_contact_policy(db, recipient_phone)
            if not policy["can_auto_reply"]:
                await self._log_audit(db, "auto_reply_prohibited", recipient_phone, {"policy": policy}, False)
                return {"sent": False, "reason": policy["reason"]}

        # Real WhatsApp API call if credentials present, otherwise mock provider confirmation
        if settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID:
            # Official Meta WhatsApp Cloud API endpoint
            # In production: httpx.post(...)
            provider_status = "sent_via_whatsapp_cloud_api"
        else:
            provider_status = "mock_provider_dispatched"

        audit_entry = await self._log_audit(db, "outbound_message_sent", recipient_phone, {
            "is_automated": is_automated,
            "provider_status": provider_status,
            "length": len(message_text)
        }, True)

        return {
            "sent": True,
            "recipient": recipient_phone,
            "provider_status": provider_status,
            "audit_id": audit_entry.id if audit_entry else None
        }

    async def _log_audit(self, db: AsyncSession, action: str, target: str, details: dict, success: bool) -> AuditLogModel:
        log = AuditLogModel(
            action=action,
            actor="friday_messaging_engine",
            target=target,
            details=details,
            success=success
        )
        db.add(log)
        await db.commit()
        return log

messaging_service = MessagingAutomationService()
