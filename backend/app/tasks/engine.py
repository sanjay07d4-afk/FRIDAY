import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List
from app.core.config import settings
from app.core.emergency import emergency_controller
from app.tools.registry import tool_registry

class TaskExecutionEngine:
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._asyncio_tasks: Dict[str, asyncio.Task] = {}
        self._listeners: List[Callable[[Dict[str, Any]], Any]] = []

    def subscribe(self, callback: Callable[[Dict[str, Any]], Any]):
        self._listeners.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], Any]):
        if callback in self._listeners:
            self._listeners.remove(callback)

    async def _emit_event(self, task_data: Dict[str, Any]):
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(task_data)
                else:
                    listener(task_data)
            except Exception as e:
                print(f"[TaskEngine] Error emitting listener: {e}")

    async def create_and_enqueue_task(
        self,
        task_type: str,
        title: str,
        payload: Dict[str, Any] = None,
        priority: str = "normal",
        timeout_seconds: float = 60.0,
        requires_confirmation: bool = False
    ) -> Dict[str, Any]:
        task_id = str(uuid.uuid4())
        initial_status = "awaiting_confirmation" if requires_confirmation else "queued"

        task_record = {
            "id": task_id,
            "type": task_type,
            "title": title,
            "status": initial_status,
            "priority": priority,
            "payload": payload or {},
            "progress": 0.0,
            "result": None,
            "error": None,
            "timeout_seconds": timeout_seconds,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        self._tasks[task_id] = task_record
        await self._emit_event(task_record)

        if not requires_confirmation:
            async_task = asyncio.create_task(self._run_task(task_id))
            self._asyncio_tasks[task_id] = async_task

        return task_record

    async def confirm_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        if not task or task["status"] != "awaiting_confirmation":
            return None

        task["status"] = "queued"
        task["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self._emit_event(task)

        async_task = asyncio.create_task(self._run_task(task_id))
        self._asyncio_tasks[task_id] = async_task
        return task

    async def cancel_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        if not task:
            return None

        if task["status"] in ["completed", "failed", "cancelled"]:
            return task

        task["status"] = "cancelled"
        task["updated_at"] = datetime.now(timezone.utc).isoformat()

        if task_id in self._asyncio_tasks:
            self._asyncio_tasks[task_id].cancel()

        await self._emit_event(task)
        return task

    async def _run_task(self, task_id: str):
        task = self._tasks[task_id]

        # 1. Emergency stop check
        if emergency_controller.is_active:
            task["status"] = "cancelled"
            task["error"] = "Execution halted: Emergency stop active"
            task["updated_at"] = datetime.now(timezone.utc).isoformat()
            await self._emit_event(task)
            return

        async with self._semaphore:
            task["status"] = "running"
            task["progress"] = 0.1
            task["updated_at"] = datetime.now(timezone.utc).isoformat()
            await self._emit_event(task)

            try:
                # Execute mapped tool if applicable
                tool_name = task["payload"].get("tool_name", task["type"])
                params = task["payload"].get("parameters", task["payload"])

                # Provide incremental progress update
                await asyncio.sleep(0.05)
                task["progress"] = 0.5
                await self._emit_event(task)

                # Check if tool is in registry
                if tool_registry.get(tool_name):
                    res = await asyncio.wait_for(
                        tool_registry.execute(tool_name, params),
                        timeout=task["timeout_seconds"]
                    )
                    if res.get("success"):
                        task["status"] = "completed"
                        task["progress"] = 1.0
                        task["result"] = res.get("output")
                    else:
                        task["status"] = "failed"
                        task["error"] = res.get("error", "Tool execution returned failure")
                else:
                    # Simulated autonomous execution for standard mocked Friday tasks
                    await asyncio.sleep(0.3)
                    task["status"] = "completed"
                    task["progress"] = 1.0
                    task["result"] = {
                        "summary": f"Task '{task['title']}' executed successfully.",
                        "data": params
                    }

            except asyncio.CancelledError:
                task["status"] = "cancelled"
                if not task.get("error"):
                    task["error"] = "Task was cancelled by user or system"
            except asyncio.TimeoutError:
                task["status"] = "failed"
                task["error"] = f"Task timed out after {task['timeout_seconds']}s"
            except Exception as e:
                task["status"] = "failed"
                task["error"] = str(e)
            finally:
                task["updated_at"] = datetime.now(timezone.utc).isoformat()
                await self._emit_event(task)
                self._asyncio_tasks.pop(task_id, None)

    async def cancel_all_active(self, reason: str = "Emergency stop activated"):
        for task_id, async_task in list(self._asyncio_tasks.items()):
            if not async_task.done():
                async_task.cancel()
            task = self._tasks.get(task_id)
            if task and task["status"] in ["queued", "running", "awaiting_confirmation"]:
                task["status"] = "cancelled"
                task["error"] = f"Execution halted: {reason}"
                task["updated_at"] = datetime.now(timezone.utc).isoformat()
                await self._emit_event(task)
        self._asyncio_tasks.clear()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(self._tasks.values())[-limit:]

task_engine = TaskExecutionEngine(max_concurrent=settings.MAX_CONCURRENT_TASKS)
emergency_controller.register_on_trigger(task_engine.cancel_all_active)
