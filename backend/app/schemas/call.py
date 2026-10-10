from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

# Call Schemas
class CallInitiateRequest(BaseModel):
    contact_name_or_number: str
    purpose: Optional[str] = None
    require_confirmation: bool = True

class CallStatusResponse(BaseModel):
    call_id: str
    target: str
    resolved_contact: Optional[str] = None
    status: str # initiating, awaiting_device, completed, failed, rejected
    platform: str = "android"
    details: Optional[Dict[str, Any]] = None

# Voice Schemas
class VoiceEnrollmentRequest(BaseModel):
    speaker_name: str
    audio_sample_base64: str

class VoiceVerificationRequest(BaseModel):
    audio_sample_base64: str
    action_type: str = "general" # general, sensitive, financial
    nonce: Optional[str] = None

class VoiceVerificationResponse(BaseModel):
    verified: bool
    confidence: float
    threshold_required: float
    speaker_id: Optional[str] = None
    anti_replay_passed: bool
    requires_secondary_auth: bool

# Device Schemas
class DeviceRegisterRequest(BaseModel):
    device_name: str
    platform: str # windows, android, web
    capabilities: List[str] = Field(default_factory=list)

class DeviceResponse(BaseModel):
    id: str
    device_name: str
    platform: str
    capabilities: List[str]
    is_active: bool
    api_key: Optional[str] = None
    last_seen: Optional[str] = None

# Emergency Stop Schemas
class EmergencyToggleRequest(BaseModel):
    activate: bool
    reason: Optional[str] = "Manual trigger via API"

class EmergencyStatusResponse(BaseModel):
    emergency_stop_active: bool
    activated_at: Optional[str] = None
    activated_by: Optional[str] = None
    reason: Optional[str] = None
