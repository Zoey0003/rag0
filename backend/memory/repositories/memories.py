from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from memory.models import ChatMessage, ChatSession, MemoryFact, User


def save_memory(
    db: Session,
    user_id: UUID,
    content: str,
    kind: str = "preference",
    source_message_id: int | None = None,
) -> MemoryFact:
    """保存长期记忆，校验来源归属，并复用完全相同的记忆。"""
    content = content.strip()

    if not content or len(content) > 1000:
        raise ValueError("记忆内容必须为 1～1000 个字符")

    if kind not in {"preference", "fact"}:
        raise ValueError("记忆类型必须为 preference 或 fact")

    if db.get(User, user_id) is None:
        raise ValueError("用户不存在")

    if source_message_id is not None:
        # 来源消息必须属于该用户，不能引用其他用户的消息。
        source = db.scalar(
            select(ChatMessage)
            .join(
                ChatSession,
                ChatMessage.session_id == ChatSession.id,
            )
            .where(
                ChatMessage.id == source_message_id,
                ChatSession.user_id == user_id,
            )
        )
        if source is None:
            raise ValueError("来源消息不存在或不属于当前用户")

    existing = db.scalar(
        select(MemoryFact)
        .where(
            MemoryFact.user_id == user_id,
            MemoryFact.kind == kind,
            MemoryFact.content == content,
        )
        .order_by(MemoryFact.created_at.asc(), MemoryFact.id.asc())
        .limit(1)
    )
    if existing is not None:
        return existing

    memory = MemoryFact(
        user_id=user_id,
        kind=kind,
        content=content,
        source_message_id=source_message_id,
    )
    db.add(memory)
    db.flush()
    return memory


def list_memories(
    db: Session,
    user_id: UUID,
    limit: int = 50,
) -> list[MemoryFact]:
    """按创建时间倒序读取用户的长期记忆。"""
    if not 1 <= limit <= 200:
        raise ValueError("limit 必须在 1～200 之间")

    if db.get(User, user_id) is None:
        raise ValueError("用户不存在")

    statement = (
        select(MemoryFact)
        .where(MemoryFact.user_id == user_id)
        .order_by(
            MemoryFact.created_at.desc(),
            MemoryFact.id.desc(),
        )
        .limit(limit)
    )
    return list(db.scalars(statement))


def delete_memory(
    db: Session,
    user_id: UUID,
    memory_id: UUID,
) -> None:
    """删除指定用户的一条长期记忆，由调用方提交事务。"""
    memory = db.scalar(
        select(MemoryFact).where(
            MemoryFact.id == memory_id,
            MemoryFact.user_id == user_id,
        )
    )
    if memory is None:
        raise ValueError("记忆不存在或不属于当前用户")

    db.delete(memory)
    db.flush()
