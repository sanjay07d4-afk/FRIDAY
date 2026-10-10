import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.contact import ContactModel
from app.models.audit import AuditLogModel
from app.core.emergency import emergency_controller

class PhoneCallService:
    """
    Phone Call Integration Service with Android Platform Boundaries:
    
    Platform Constraints:
    - Direct outgoing calls on Android require user confirmation and TELECOM/CALL_PHONE runtime permissions.
    - Resolves spoken contact names carefully, rejecting ambiguous matches.
    - Complies with Android security guidelines.
    """

    async def resolve_contact(self, db: AsyncSession, query: str) -> Dict[str, Any]:
        """
        Matches a spoken or typed name against contacts.
        Handles ambiguous matches gracefully.
        """
        clean_query = query.strip()
        pattern = f"%{clean_query}%"

        stmt = select(ContactModel).where(ContactModel.name.ilike(pattern))
        result = await db.execute(stmt)
        matches = list(result.scalars().all())

        if not matches:
            # Check if query is already an E.164 phone number
            if clean_query.startswith("+") or clean_query.isdigit():
                return {
                    "status": "direct_number",
                    "contact_name": "Direct Dial",
                    "phone_number": clean_query,
                    "is_ambiguous": False
                }
            return {
                "status": "not_found",
                "is_ambiguous": False,
                "message": f"No contact matching '{query}' was found in your address book."
            }

        if len(matches) > 1:
            return {
                "status": "ambiguous",
                "is_ambiguous": True,
                "candidates": [m.to_dict() for m in matches],
                "message": f"Found {len(matches)} contacts matching '{query}'. Please specify which one."
            }

        contact = matches[0]
        return {
            "status": "resolved",
            "contact_name": contact.name,
            "phone_number": contact.phone_number,
            "is_saved": contact.is_saved,
            "is_ambiguous": False
        }

    async def initiate_call_workflow(
        self,
        db: AsyncSession,
        contact_query: str,
        purpose: Optional[str] = None
    ) -> Dict[str, Any]:
        if emergency_controller.is_active:
            return {"status": "blocked", "message": "Emergency stop is active. Call request halted."}

        resolution = await self.resolve_contact(db, contact_query)
        if resolution.get("is_ambiguous") or resolution.get("status") == "not_found":
            return resolution

        call_id = str(uuid.uuid4())
        phone = resolution.get("phone_number")
        name = resolution.get("contact_name")

        # Android integration contract: Create pending intent awaiting companion client confirmation
        log = AuditLogModel(
            action="phone_call_initiated",
            actor="user",
            target=phone,
            details={"contact_name": name, "purpose": purpose, "call_id": call_id},
            success=True
        )
        db.add(log)
        await db.commit()

        return {
            "call_id": call_id,
            "status": "awaiting_device_confirmation",
            "contact_name": name,
            "phone_number": phone,
            "platform_target": "android_companion",
            "message": f"Call intent created for {name} ({phone}). Ready to dispatch to Android companion."
        }

phone_call_service = PhoneCallService()
