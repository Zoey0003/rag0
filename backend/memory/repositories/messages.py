from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from memory.models import ChatMessage
from memory.repositories.sessions import get_session


def save_message(
    db: Session,
    user_id: UUID,
    session_id: UUID,
    role: str,
    content: str,
    sources: list[dict] | None = None,
    status: str = "success",
) -> ChatMessage:
    """保存消息，并更新所属会话的最近活动时间。"""
    if role not in {"user", "assistant"}:
        raise ValueError("role 必须为 user 或 assistant")

    if status not in {"pending", "success", "failed"}:
        raise ValueError("消息状态必须为 pending、success 或 failed")

    if not content.strip():
        raise ValueError("消息内容不能为空")

    chat_session = get_session(db, user_id, session_id)

    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        sources=sources if sources is not None else [],
        status=status,
    )
    db.add(message)

    # 插入消息不会自动更新会话表，需要显式修改。
    chat_session.updated_at = func.now()

    db.flush()
    return message


def list_all_messages(
    db: Session,
    user_id: UUID,
    session_id: UUID,
) -> list[ChatMessage]:
    """读取完整会话历史，供导出使用，不受页面分页限制。"""
    get_session(db, user_id, session_id)
    statement = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.asc())
    )
    return list(db.scalars(statement))


def list_messages(
    db: Session,
    user_id: UUID,
    session_id: UUID,
    limit: int = 100,
    before_id: int | None = None,
) -> list[ChatMessage]:
    """查询最近一页消息，按从旧到新返回，支持向前翻页。"""
    if not 1 <= limit <= 500:
        raise ValueError("limit 必须在 1～500 之间")

    # 读取消息前，先检查会话是否属于当前用户。
    get_session(db, user_id, session_id)

    statement = select(ChatMessage).where(
        ChatMessage.session_id == session_id
    )

    if before_id is not None:
        statement = statement.where(ChatMessage.id < before_id)

    statement = statement.order_by(ChatMessage.id.desc()).limit(limit)
    messages = list(db.scalars(statement))

    # 倒序查询最近消息，再恢复成聊天展示顺序。
    messages.reverse()
    return messages
