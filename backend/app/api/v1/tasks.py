from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.schemas.task import TaskCreate, TaskResponse, TaskBatchRequest
from app.tasks.engine import task_engine
from app.core.security import verify_auth

router = APIRouter(prefix="/tasks", tags=["Task Engine"])

@router.post("", response_model=TaskResponse)
async def create_task(task_in: TaskCreate, auth: dict = Depends(verify_auth)):
    """Create and enqueue a new task in the execution engine."""
    task = await task_engine.create_and_enqueue_task(
        task_type=task_in.type,
        title=task_in.title,
        payload=task_in.payload,
        priority=task_in.priority,
        timeout_seconds=task_in.timeout_seconds
    )
    return task

@router.post("/batch", response_model=List[TaskResponse])
async def create_task_batch(batch_in: TaskBatchRequest, auth: dict = Depends(verify_auth)):
    """Enqueues multiple independent tasks to execute concurrently."""
    spawned = []
    for item in batch_in.tasks:
        task = await task_engine.create_and_enqueue_task(
            task_type=item.type,
            title=item.title,
            payload=item.payload,
            priority=item.priority,
            timeout_seconds=item.timeout_seconds
        )
        spawned.append(task)
    return spawned

@router.get("", response_model=List[TaskResponse])
async def list_tasks(limit: int = 50, auth: dict = Depends(verify_auth)):
    """List recent tasks and their real-time execution states."""
    return task_engine.list_tasks(limit=limit)

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, auth: dict = Depends(verify_auth)):
    task = task_engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: str, auth: dict = Depends(verify_auth)):
    task = await task_engine.cancel_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/{task_id}/confirm", response_model=TaskResponse)
async def confirm_task(task_id: str, auth: dict = Depends(verify_auth)):
    task = await task_engine.confirm_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or not awaiting confirmation")
    return task
