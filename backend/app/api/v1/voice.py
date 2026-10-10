import base64
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Dict, Any
from app.voice.stt import get_stt_provider
from app.voice.tts import get_tts_provider
from app.voice.verification import speaker_authenticator
from app.voice.session import voice_session
from app.schemas.call import (
    VoiceEnrollmentRequest,
    VoiceVerificationRequest,
    VoiceVerificationResponse
)
from app.core.security import verify_auth

router = APIRouter(prefix="/voice", tags=["Voice Assistant & Verification"])

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    auth: dict = Depends(verify_auth)
):
    """Transcribe user audio to text."""
    stt = get_stt_provider()
    content = await file.read()
    res = await stt.transcribe_audio(content)
    return res

@router.post("/synthesize")
async def synthesize_speech(
    text: str = Form(...),
    voice_name: str = Form("en-US-Friday"),
    auth: dict = Depends(verify_auth)
):
    """Synthesize text into speech."""
    tts = get_tts_provider()
    res = await tts.synthesize_speech(text, voice_name=voice_name)
    return res

@router.post("/enroll")
async def enroll_voice_profile(
    req: VoiceEnrollmentRequest,
    auth: dict = Depends(verify_auth)
):
    """Enroll authorized speaker acoustic signature."""
    try:
        sample_bytes = base64.b64decode(req.audio_sample_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 audio payload")

    res = speaker_authenticator.enroll_speaker(req.speaker_name, sample_bytes)
    return res

@router.post("/verify", response_model=VoiceVerificationResponse)
async def verify_speaker(
    req: VoiceVerificationRequest,
    auth: dict = Depends(verify_auth)
):
    """Verify speaker biometric match against confidence threshold."""
    try:
        sample_bytes = base64.b64decode(req.audio_sample_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 audio payload")

    res = speaker_authenticator.verify_voice(sample_bytes, action_type=req.action_type, nonce=req.nonce)
    return VoiceVerificationResponse(
        verified=res["verified"],
        confidence=res["confidence"],
        threshold_required=res["threshold_required"],
        speaker_id=res.get("speaker_id"),
        anti_replay_passed=res["anti_replay_passed"],
        requires_secondary_auth=res["requires_secondary_auth"]
    )

@router.get("/session-state")
async def get_voice_session_state(auth: dict = Depends(verify_auth)):
    """Retrieve current voice session state (idle, listening, processing, speaking)."""
    return {
        "session_id": voice_session.session_id,
        "state": voice_session.state,
        "last_activity": voice_session.last_activity
    }
