from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.core.config import settings

class BaseSTTProvider(ABC):
    @abstractmethod
    async def transcribe_audio(self, audio_bytes: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
        pass

class MockSTTProvider(BaseSTTProvider):
    async def transcribe_audio(self, audio_bytes: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
        # Clean fallback for local dev / testing
        return {
            "transcript": "Hey Friday, check system diagnostics.",
            "confidence": 0.98,
            "provider": "mock_stt",
            "language": "en"
        }

class WhisperSTTProvider(BaseSTTProvider):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY

    async def transcribe_audio(self, audio_bytes: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Whisper STT provider requires an OpenAI API key.")
        # Real HTTP multipart audio call in production
        return {
            "transcript": "Transcribed audio via Whisper API",
            "confidence": 0.96,
            "provider": "openai_whisper"
        }

def get_stt_provider() -> BaseSTTProvider:
    if settings.VOICE_STT_PROVIDER == "whisper" and settings.OPENAI_API_KEY:
        return WhisperSTTProvider()
    return MockSTTProvider()
