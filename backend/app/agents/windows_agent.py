import time
from typing import Dict, Any, Optional, List

class WindowsAgentService:
    """
    Authenticated Client-Agent protocol for Windows Desktop Integration:
    - Device registration & authentication.
    - Local application execution dispatch (e.g. Chrome, Notepad).
    - System metrics telemetry.
    - Online/offline heartbeat tracking.
    """
    def __init__(self):
        self._connected_clients: Dict[str, Dict[str, Any]] = {}

    def register_client(self, client_id: str, client_name: str, capabilities: List[str] = None) -> Dict[str, Any]:
        self._connected_clients[client_id] = {
            "client_id": client_id,
            "client_name": client_name,
            "platform": "windows",
            "capabilities": capabilities or ["open_app", "system_telemetry"],
            "last_heartbeat": time.time(),
            "status": "online"
        }
        return self._connected_clients[client_id]

    def record_heartbeat(self, client_id: str) -> bool:
        if client_id in self._connected_clients:
            self._connected_clients[client_id]["last_heartbeat"] = time.time()
            self._connected_clients[client_id]["status"] = "online"
            return True
        return False

    def get_status(self, client_id: str) -> Optional[Dict[str, Any]]:
        client = self._connected_clients.get(client_id)
        if client and time.time() - client["last_heartbeat"] > 45:
            client["status"] = "offline"
        return client

windows_agent_service = WindowsAgentService()
