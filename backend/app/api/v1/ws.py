import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.tasks.engine import task_engine
from app.voice.session import voice_session

router = APIRouter(tags=["WebSockets"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, data: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# Hook task engine events to WebSocket broadcast
async def on_task_engine_event(task_record: dict):
    await manager.broadcast_json({
        "event_type": "task_update",
        "task": task_record
    })

task_engine.subscribe(on_task_engine_event)

@router.websocket("/ws/tasks")
async def websocket_tasks_endpoint(websocket: WebSocket):
    """
    WebSocket channel for real-time task progress, status transitions, and HUD notifications.
    """
    await manager.connect(websocket)
    try:
        # Send initial snapshot of active tasks
        tasks = task_engine.list_tasks(limit=20)
        await websocket.send_json({
            "event_type": "initial_snapshot",
            "tasks": tasks
        })

        while True:
            # Keep-alive ping loop & client incoming messages
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "ping":
                    await websocket.send_json({"event_type": "pong"})
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
