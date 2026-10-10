import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any

class EmergencyStopController:
    """
    Central kill-switch controller for FRIDAY.
    When emergency stop is triggered, all running automated tasks,
    outgoing messaging, and execution tools are halted immediately.
    """
    def __init__(self, initial_state: bool = False):
        self._is_active: bool = initial_state
        self._activated_at: Optional[datetime] = None
        self._activated_by: Optional[str] = None
        self._reason: Optional[str] = None
        self._lock = asyncio.Lock()
        self._callbacks: list = []

    def register_on_trigger(self, callback):
        self._callbacks.append(callback)

    @property
    def is_active(self) -> bool:
        return self._is_active

    async def trigger(self, triggered_by: str = "user", reason: str = "Manual emergency stop triggered") -> Dict[str, Any]:
        async with self._lock:
            self._is_active = True
            self._activated_at = datetime.now(timezone.utc)
            self._activated_by = triggered_by
            self._reason = reason

            for cb in self._callbacks:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(reason)
                    else:
                        cb(reason)
                except Exception as e:
                    print(f"[EmergencyController] Callback error: {e}")

            return self.get_status()

    async def reset(self, reset_by: str = "user") -> Dict[str, Any]:
        async with self._lock:
            self._is_active = False
            self._activated_at = None
            self._activated_by = None
            self._reason = None
            return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        return {
            "emergency_stop_active": self._is_active,
            "activated_at": self._activated_at.isoformat() if self._activated_at else None,
            "activated_by": self._activated_by,
            "reason": self._reason,
        }

emergency_controller = EmergencyStopController()
