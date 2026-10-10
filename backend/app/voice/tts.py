from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.core.config import settings

class BaseTTSProvider(ABC):
    @abstractmethod
    async def synthesize_speech(self, text: str, voice_name: str = "en-US-Friday") -> Dict[str, Any]:
        pass

class MockTTSProvider(BaseTTSProvider):
    async def synthesize_speech(self, text: str, voice_name: str = "en-US-Friday") -> Dict[str, Any]:
        # Returns simulated audio metadata; client browser uses Web Speech Synthesis
        return {
            "text": text,
            "voice": voice_name,
            "audio_format": "audio/mp3",
            "audio_base64": None,
            "use_client_speech_synth": True,
            "provider": "mock_tts"
        }

class ElevenLabsTTSProvider(BaseTTSProvider):
    def __init__(self, api_key: str = None):
        self.api_key = api_key

    async def synthesize_speech(self, text: str, voice_name: str = "Friday") -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("ElevenLabs TTS provider requires an API key.")
        return {
            "text": text,
            "voice": voice_name,
            "audio_format": "audio/mp3",
            "audio_base64": "UklGR...",
            "use_client_speech_synth": False,
            "provider": "elevenlabs"
        }

def get_tts_provider() -> BaseTTSProvider:
    return MockTTSProvider()
