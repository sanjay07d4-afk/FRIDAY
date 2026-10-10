import asyncio
import time
from typing import Dict, Any, Optional, Callable, List

class VoiceSessionState:
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"

class VoiceSessionManager:
    """
    Manages active voice conversation sessions, wake-word detections,
    voice activity detection (VAD), and streaming state transitions.
    """
    def __init__(self, session_id: str = "default_voice_session"):
        self.session_id = session_id
        self.state = VoiceSessionState.IDLE
        self.last_activity = time.time()
        self._listeners: List[Callable[[str], Any]] = []

    def set_state(self, new_state: str):
        self.state = new_state
        self.last_activity = time.time()
        for l in self._listeners:
            try:
                l(self.state)
            except Exception as e:
                print(f"[VoiceSession] Error in listener: {e}")

    def on_wake_word_detected(self):
        """Transition from IDLE to LISTENING when 'Hey Friday' is triggered"""
        self.set_state(VoiceSessionState.LISTENING)

    def on_user_speech_ended(self):
        """Transition from LISTENING to PROCESSING when speech terminates"""
        self.set_state(VoiceSessionState.PROCESSING)

    def on_assistant_speaking_started(self):
        """Transition from PROCESSING to SPEAKING when audio playback begins"""
        self.set_state(VoiceSessionState.SPEAKING)

    def on_user_interruption(self):
        """Barge-in / interruption support: Stop assistant speaking immediately"""
        self.set_state(VoiceSessionState.INTERRUPTED)
        self.set_state(VoiceSessionState.LISTENING)

    def on_cycle_complete(self):
        """Return to IDLE state after speaking finishes"""
        self.set_state(VoiceSessionState.IDLE)

voice_session = VoiceSessionManager()
