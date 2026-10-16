from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.db.session import SessionLocal
from app.modules.auth.dependencies import require_user_id
from app.modules.memory import repository
from app.modules.memory.schemas import CreateMemoryRequest


router = APIRouter(
    prefix="/memory/facts",
    tags=["长期记忆"],
)


@router.post("")
def create_memory_fact(
    request: CreateMemoryRequest,
    user_id:UUID=Depends(require_user_id)):
    """保存长期记忆；完全相同的内容复用已有记录。"""
    try:
        with SessionLocal.begin() as db:
            memory = repository.save_memory(
                db,
                user_id=user_id,
                content=request.content,
                kind=request.kind,
                source_message_id=request.source_message_id,
            )
            result = {
                "memory_id": str(memory.id),
                "kind": memory.kind,
                "content": memory.content,
                "source_message_id": memory.source_message_id,
                "created_at": memory.created_at,
            }
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.get("")
def list_memory_facts(user_id: UUID=Depends(require_user_id)):
    """查询当前用户最近的长期记忆。"""
    try:
        with SessionLocal() as db:
            memories = repository.list_memories(db, user_id)
            return [
                {
                    "memory_id": str(item.id),
                    "kind": item.kind,
                    "content": item.content,
                    "source_message_id": item.source_message_id,
                    "created_at": item.created_at,
                }
                for item in memories
            ]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

@router.delete("/memory/facts/{memory_id}")
def delete_memory_fact(memory_id: UUID, user_id: UUID=Depends(require_user_id)):
    """删除一条属于指定用户的长期记忆。"""
    try:
        with SessionLocal.begin() as db:
            repository.delete_memory(db, user_id, memory_id)
        return {"message": "记忆已删除"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
