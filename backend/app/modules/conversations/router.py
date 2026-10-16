from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.db.session import SessionLocal
from app.modules.auth.dependencies import require_user_id
from app.modules.conversations import repository
from app.modules.conversations.schemas import (
    CreateMemorySessionRequest,
    RenameMemorySessionRequest,
)

from app.core.concurrency import graph_lock
from app.modules.conversations.export_service import export_session_markdown

router = APIRouter(
    prefix="/memory/sessions",
    tags=["会话管理"],
)


@router.post("", status_code=201)
def create_memory_session(
    request: CreateMemorySessionRequest,
    user_id: UUID=Depends(require_user_id)                      ):
    """创建数据库会话，并返回会话 ID。"""
    try:
        with SessionLocal.begin() as db:
            chat_session = repository.create_session(
                db,
                user_id=user_id,
                title=request.title,
            )
            result = {
                "session_id": str(chat_session.id),
                "user_id": str(chat_session.user_id),
                "title": chat_session.title,
                "created_at": chat_session.created_at,
            }
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.get("")
def list_memory_sessions(user_id: UUID=Depends(require_user_id)):
    """读取用户的数据库会话列表，按最近活动时间排序。"""
    with SessionLocal() as db:
        chat_sessions = repository.list_sessions(db, user_id)
        return [
            {
                "session_id": str(item.id),
                "title": item.title,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in chat_sessions
        ]

@router.patch("/{session_id}")
def rename_memory_session(
    session_id: UUID,
    request: RenameMemorySessionRequest,
    user_id: UUID=Depends(require_user_id),
):
    """修改会话标题，不修改历史消息。"""
    title = request.title.strip()
    if not title:
        raise HTTPException(
            status_code=422,
            detail="会话标题不能为空",
        )

    try:
        with SessionLocal.begin() as db:
            chat_session = repository.rename_session(
                db,
                user_id=user_id,
                session_id=session_id,
                title=title,
            )
            result = {
                "session_id": str(chat_session.id),
                "title": chat_session.title,
                "created_at": chat_session.created_at,
                "updated_at": chat_session.updated_at,
            }

        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from None

@router.get("/{session_id}/messages")
def list_memory_messages(
    session_id: UUID,
    user_id: UUID=Depends(require_user_id),
    limit: int = 100,
    before_id: int | None = None,
):
    """读取一页会话历史；传入最早消息 ID 可继续向前翻页。"""
    try:
        with SessionLocal() as db:
            messages = repository.list_messages(
                db,
                user_id=user_id,
                session_id=session_id,
                limit=limit,
                before_id=before_id,
            )
            return [
                {
                    "id": item.id,
                    "role": item.role,
                    "content": item.content,
                    "status": item.status,
                    "sources": item.sources,
                    "created_at": item.created_at,
                }
                for item in messages
            ]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.delete("/{session_id}")
def delete_memory_session(
    session_id: UUID, 
    user_id: UUID=Depends(require_user_id)):
    """删除会话及消息，保留长期记忆。"""
    try:
        with graph_lock:
            with SessionLocal.begin() as db:
                repository.delete_session(
                    db,
                    user_id=user_id,
                    session_id=session_id,
                )
        return {"session_id": str(session_id), "status": "deleted"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.get("/{session_id}/export")
def export_memory_session(session_id: UUID, user_id: UUID=Depends(require_user_id)):
    """读取完整会话并返回 Markdown 文件内容。"""
    try:
        # 与问答和删除共用锁，避免导出到尚未完成的一轮消息。
        with graph_lock:
            with SessionLocal() as db:
                return export_session_markdown(db, user_id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


