from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemoryResponse
from app.memory.service import memory_service
from app.core.security import verify_auth

router = APIRouter(prefix="/memory", tags=["Personal Memory System"])

@router.post("", response_model=MemoryResponse)
async def create_memory(
    mem_in: MemoryCreate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """Store user-approved memory with categories (fact, preference, instruction, summary)."""
    user_id = auth.get("sub", "default_user")
    try:
        mem = await memory_service.save_memory(
            db=db,
            content=mem_in.content,
            category=mem_in.category,
            user_id=user_id,
            metadata=mem_in.metadata
        )
        return mem.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[MemoryResponse])
async def list_memories(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """List persistent saved memories for the authenticated user."""
    user_id = auth.get("sub", "default_user")
    mems = await memory_service.list_memories(db=db, user_id=user_id, category=category, limit=limit)
    return [m.to_dict() for m in mems]

@router.get("/search", response_model=List[MemoryResponse])
async def search_memories(
    q: str = Query(..., min_length=1),
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """Search user memories via keyword matching."""
    user_id = auth.get("sub", "default_user")
    mems = await memory_service.search_memories(db=db, query=q, user_id=user_id, limit=limit)
    return [m.to_dict() for m in mems]

@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: str,
    update_in: MemoryUpdate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """Update or correct a saved memory."""
    user_id = auth.get("sub", "default_user")
    mem = await memory_service.update_memory(
        db=db,
        memory_id=memory_id,
        new_content=update_in.content,
        new_category=update_in.category,
        user_id=user_id
    )
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    return mem.to_dict()

@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    hard_delete: bool = False,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """Delete a memory upon explicit user request."""
    user_id = auth.get("sub", "default_user")
    deleted = await memory_service.delete_memory(db=db, memory_id=memory_id, hard_delete=hard_delete, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "success", "message": f"Memory '{memory_id}' deleted."}

@router.get("/export")
async def export_memories(
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(verify_auth)
):
    """Export all user memory records for complete user data control."""
    user_id = auth.get("sub", "default_user")
    return await memory_service.export_all(db=db, user_id=user_id)
