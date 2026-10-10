from typing import List, Dict, Any, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.memory import MemoryModel
import re

class MemoryService:
    """
    Persistent, user-controlled memory service for FRIDAY.
    Saves approved facts, preferences, instructions, and conversation summaries.
    Enforces strict privacy and instant deletion upon user request.
    """

    FORBIDDEN_KEYWORDS = ["password", "pin", "cvv", "credit card", "api_key", "secret_key"]

    async def save_memory(
        self,
        db: AsyncSession,
        content: str,
        category: str = "fact",
        user_id: str = "default_user",
        metadata: Dict[str, Any] = None
    ) -> MemoryModel:
        # Privacy filter: never save auth secrets or credit card details
        lower_content = content.lower()
        for kw in self.FORBIDDEN_KEYWORDS:
            if kw in lower_content:
                raise ValueError(f"Privacy policy violation: Content contains forbidden sensitive credential keyword '{kw}'")

        memory = MemoryModel(
            user_id=user_id,
            category=category,
            content=content.strip(),
            extra_metadata=metadata or {},
            is_deleted=False
        )
        db.add(memory)
        await db.commit()
        await db.refresh(memory)
        return memory

    async def list_memories(
        self,
        db: AsyncSession,
        user_id: str = "default_user",
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[MemoryModel]:
        stmt = select(MemoryModel).where(
            MemoryModel.user_id == user_id,
            MemoryModel.is_deleted == False
        )
        if category:
            stmt = stmt.where(MemoryModel.category == category)
        stmt = stmt.order_by(MemoryModel.created_at.desc()).limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def search_memories(
        self,
        db: AsyncSession,
        query: str,
        user_id: str = "default_user",
        limit: int = 10
    ) -> List[MemoryModel]:
        pattern = f"%{query.strip()}%"
        stmt = select(MemoryModel).where(
            MemoryModel.user_id == user_id,
            MemoryModel.is_deleted == False,
            MemoryModel.content.ilike(pattern)
        ).limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_memory(
        self,
        db: AsyncSession,
        memory_id: str,
        new_content: Optional[str] = None,
        new_category: Optional[str] = None,
        user_id: str = "default_user"
    ) -> Optional[MemoryModel]:
        stmt = select(MemoryModel).where(
            MemoryModel.id == memory_id,
            MemoryModel.user_id == user_id,
            MemoryModel.is_deleted == False
        )
        result = await db.execute(stmt)
        memory = result.scalar_one_or_none()
        if not memory:
            return None

        if new_content:
            memory.content = new_content.strip()
        if new_category:
            memory.category = new_category

        await db.commit()
        await db.refresh(memory)
        return memory

    async def delete_memory(
        self,
        db: AsyncSession,
        memory_id: str,
        hard_delete: bool = False,
        user_id: str = "default_user"
    ) -> bool:
        stmt = select(MemoryModel).where(
            MemoryModel.id == memory_id,
            MemoryModel.user_id == user_id
        )
        result = await db.execute(stmt)
        memory = result.scalar_one_or_none()
        if not memory:
            return False

        if hard_delete:
            await db.delete(memory)
        else:
            memory.is_deleted = True

        await db.commit()
        return True

    async def export_all(
        self,
        db: AsyncSession,
        user_id: str = "default_user"
    ) -> List[Dict[str, Any]]:
        memories = await self.list_memories(db, user_id=user_id, limit=500)
        return [m.to_dict() for m in memories]

memory_service = MemoryService()
